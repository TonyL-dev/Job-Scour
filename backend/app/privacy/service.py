import base64
import hashlib
import hmac
import os
import secrets
import time
from typing import Protocol
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.encryption import key
from app.core.workspace import WorkspaceBarrier, bind
from app.privacy import repository as repo
from app.privacy.schemas import PrivacyStatus
from app.rendering.service import clear_cache


def hash_passcode(value: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(value.encode(), salt=salt, n=16384, r=8, p=1)
    return "scrypt:1:" + base64.b64encode(salt + digest).decode()


def verify(value: str, encoded: str) -> bool:
    if not encoded.startswith("scrypt:1:"):
        return False
    try:
        raw = base64.b64decode(encoded.removeprefix("scrypt:1:"), validate=True)
        return hmac.compare_digest(
            raw[16:], hashlib.scrypt(value.encode(), salt=raw[:16], n=16384, r=8, p=1)
        )
    except (ValueError, TypeError):
        return False


class LockState:
    def __init__(self, encoded: str | None) -> None:
        self.encoded = encoded
        self.sessions: dict[str, float] = {}
        self.failures = 0
        self.retry_at = 0.0

    def unlocked(self, token: str | None) -> bool:
        expired = [t for t, expiry in self.sessions.items() if expiry <= time.monotonic()]
        if expired:
            for t in expired:
                del self.sessions[t]
            clear_cache()
        return not self.encoded or bool(token and self.sessions.get(token, 0) > time.monotonic())

    def unlock(self, value: str) -> str:
        if time.monotonic() < self.retry_at:
            raise HTTPException(429, "Wait before another unlock attempt")
        if not self.encoded or not verify(value, self.encoded):
            self.failures += 1
            self.retry_at = time.monotonic() + min(60, 2 ** min(self.failures, 6))
            raise HTTPException(401, "Invalid passcode")
        self.failures = 0
        self.retry_at = 0
        self.sessions = {
            t: expiry for t, expiry in self.sessions.items() if expiry > time.monotonic()
        }
        token = secrets.token_urlsafe(32)
        self.sessions[token] = time.monotonic() + 1800
        return token


def status(state: LockState, token: str | None) -> PrivacyStatus:
    return PrivacyStatus(
        passcode_enabled=bool(state.encoded),
        locked=not state.unlocked(token),
        encryption_enabled=key() is not None,
        database_encrypted=bool(os.environ.get("APP_DATABASE_PASSPHRASE")),
    )


def configure(
    db: Session,
    owner: UUID,
    state: LockState,
    value: str,
    current: str | None,
    barrier: WorkspaceBarrier,
) -> str:
    if state.encoded and (not current or not verify(current, state.encoded)):
        raise HTTPException(401, "Current passcode required")
    encoded = hash_passcode(value)
    repo.set_passcode(db, owner, encoded)
    state.encoded = encoded
    state.sessions.clear()
    clear_cache()
    barrier.invalidate()
    return state.unlock(value)


def export(db: Session, owner: UUID) -> dict[str, object]:
    return repo.export(db, owner)


def delete_all(db: Session, owner: UUID, confirmation: str) -> None:
    if confirmation != "DELETE ALL MY DATA":
        raise HTTPException(422, "Type DELETE ALL MY DATA to confirm")
    repo.delete_all(db, owner)


def archive(db: Session, owner: UUID) -> bytes:
    import json
    from io import BytesIO
    from zipfile import ZIP_DEFLATED, ZipFile

    from app.resumes import service as resumes

    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as bundle:
        bundle.writestr("data.json", json.dumps(export(db, owner), ensure_ascii=False, indent=2))
        for document in resumes.list_resumes(db, owner):
            for version in resumes.history(db, owner, document.id):
                pdf = resumes.render(version.content).pdf
                bundle.writestr(
                    f"pdfs/{document.id}/v{version.version_number}-{version.id}.pdf", pdf
                )
        from app.cover_letters import service as letters

        for letter_version in letters.list_versions(db, owner):
            bundle.writestr(
                f"letters/{letter_version.document_id}/"
                f"v{letter_version.version_number}-{letter_version.id}.pdf",
                letters.render(letter_version.content).pdf,
            )
    return output.getvalue()


class RunController(Protocol):
    async def close(self) -> None: ...


class PrivacyRuntime(Protocol):
    lock: LockState
    barrier: WorkspaceBarrier
    runs: RunController
    deleting: bool


async def cancel_pending(runtime: PrivacyRuntime) -> None:
    from app.ai.operations import cancel_all as cancel_operations
    from app.auth.repository import LOCAL_OWNER
    from app.cover_letters.repository import cancel_pending as cancel_letters
    from app.importers.repository import recover_parsing
    from app.importers.service import cancel_all

    await cancel_all()
    await cancel_operations()
    await runtime.runs.close()
    engine = getattr(runtime, "engine", None)
    if engine is not None:
        with Session(engine) as control:
            bind(control, runtime.barrier)
            cancel_letters(control, LOCAL_OWNER)
            recover_parsing(control, LOCAL_OWNER)


async def lock_workspace(runtime: PrivacyRuntime) -> None:
    runtime.lock.sessions.clear()
    clear_cache()
    runtime.barrier.invalidate()
    await cancel_pending(runtime)


async def delete_workspace(
    db: Session, owner: UUID, runtime: PrivacyRuntime, confirmation: str
) -> None:
    if confirmation != "DELETE ALL MY DATA":
        raise HTTPException(422, "Type DELETE ALL MY DATA to confirm")
    runtime.deleting = True
    clear_cache()
    epoch = runtime.barrier.invalidate()
    bind(db, runtime.barrier, epoch)
    try:
        from app.ai.operations import cancel_all as cancel_operations
        from app.importers.service import cancel_all

        await cancel_all()
        await cancel_operations()
        await runtime.runs.close()
        delete_all(db, owner, confirmation)
    finally:
        runtime.deleting = False
