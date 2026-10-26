import asyncio
import base64
import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from threading import BoundedSemaphore, Lock
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.ai.gateway import Gateway
from app.ai.generation import numbers
from app.ai.phase6 import extract_import, provenance
from app.career import service as career
from app.career.schemas import CareerInput
from app.core.workspace import validate_session
from app.importers import repository
from app.importers.schemas import Candidate, Fragment, ImportRun, Review, Upload
from app.settings import service as settings

ADMISSION = BoundedSemaphore(2)
ADAPTER: TypeAdapter[CareerInput] = TypeAdapter(CareerInput)
ACTIVE: dict[tuple[UUID, UUID], asyncio.Task[object]] = {}
PARSERS: dict[tuple[UUID, UUID], subprocess.Popen[bytes]] = {}
PARSER_LOCK = Lock()
CANCELLED: set[tuple[UUID, UUID]] = set()


def list_runs(db: Session, owner: UUID) -> list[ImportRun]:
    return repository.list_runs(db, owner)


def get(db: Session, owner: UUID, identifier: UUID) -> ImportRun:
    return repository.get(db, owner, identifier)


def remove_original(db: Session, owner: UUID, identifier: UUID) -> None:
    repository.remove_original(db, owner, identifier)


async def cancel_all() -> None:
    with PARSER_LOCK:
        CANCELLED.intersection_update(PARSERS)
        for key, process in list(PARSERS.items()):
            CANCELLED.add(key)
            if process.poll() is None:
                process.kill()
    tasks = list(ACTIVE.values())
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


def cancel(db: Session, owner: UUID, identifier: UUID) -> None:
    run = repository.get(db, owner, identifier)
    if run.status == "parsing":
        with PARSER_LOCK:
            CANCELLED.add((owner, identifier))
            process = PARSERS.get((owner, identifier))
            if process and process.poll() is None:
                process.kill()
        repository.fail_parse(db, owner, identifier, "Parsing cancelled; upload again")
    task = ACTIVE.get((owner, identifier))
    if task:
        task.cancel()


def upload_key() -> bytes:
    raw = os.environ.get("APP_UPLOAD_KEY") or os.environ.get("APP_ENCRYPTION_KEY")
    try:
        result = base64.b64decode(raw or "", validate=True)
        if len(result) != 32:
            raise ValueError()
        return result
    except ValueError as error:
        raise HTTPException(
            503, "Retaining uploads requires APP_UPLOAD_KEY (base64 of 32 random bytes)"
        ) from error


def parse(
    content: bytes, kind: str, token: tuple[UUID, UUID], guard: Callable[[], None]
) -> list[Fragment]:
    if not ADMISSION.acquire(blocking=False):
        raise HTTPException(429, "Document parser busy; retry shortly")
    try:
        child_env = {
            k: v
            for k, v in os.environ.items()
            if k.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH"}
        }
        with PARSER_LOCK:
            guard()
            process = subprocess.Popen(
                [sys.executable, "-I", str(Path(__file__).with_name("parser.py")), kind],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=child_env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            PARSERS[token] = process
            if token in CANCELLED:
                process.kill()
        try:
            output, _diagnostics = process.communicate(content, timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise
        if token in CANCELLED:
            raise HTTPException(409, "Parsing cancelled; no facts saved")
        if process.returncode or len(output) > 1500000:
            raise HTTPException(
                422,
                "Unsupported, corrupt, encrypted or oversized document. "
                "Text PDF/DOCX only; OCR is unsupported.",
            )
        return [Fragment.model_validate(f) for f in json.loads(output)["fragments"]]
    except subprocess.TimeoutExpired as error:
        raise HTTPException(
            422, "Document parsing exceeded 15 seconds; retry when less busy or simplify the file"
        ) from error
    finally:
        with PARSER_LOCK:
            PARSERS.pop(token, None)
            CANCELLED.discard(token)
        ADMISSION.release()


def upload(db: Session, owner: UUID, data: Upload) -> ImportRun:
    name = data.filename
    if "/" in name or "\\" in name or any(ord(c) < 32 for c in name):
        raise HTTPException(422, "Use a filename without paths or control characters")
    kind = "pdf" if data.mime == "application/pdf" else "docx"
    if not name.lower().endswith("." + kind):
        raise HTTPException(422, "Filename and document type do not agree")
    try:
        content = base64.b64decode(data.content_base64, validate=True)
    except ValueError as error:
        raise HTTPException(422, "Invalid base64 upload") from error
    if not content or len(content) > 2 * 1024 * 1024:
        raise HTTPException(413, "Upload limit is 2 MiB")
    secret = upload_key() if data.retain_original else None
    run = repository.create(
        db, owner, name, data.mime, {"fragments": [], "candidates": [], "saved_ids": []}, None
    )
    try:
        fragments = parse(content, kind, (owner, run.id), lambda: validate_session(db))
    except HTTPException as error:
        validate_session(db)
        repository.fail_parse(db, owner, run.id, str(error.detail))
        raise
    except Exception as error:
        validate_session(db)
        repository.fail_parse(
            db, owner, run.id, "Parser unavailable; retry after checking runtime setup"
        )
        raise HTTPException(
            503, "Parser unavailable; retry after checking runtime setup"
        ) from error
    original = None
    if secret:
        nonce = os.urandom(12)
        original = nonce + AESGCM(secret).encrypt(
            nonce, content, b"stonks.upload.v1:" + str(owner).encode()
        )
    validate_session(db)
    return repository.finish_parse(
        db,
        owner,
        run.id,
        {"fragments": [f.model_dump() for f in fragments], "candidates": [], "saved_ids": []},
        original,
    )


def validate_candidates(run: ImportRun, candidates: list[Candidate]) -> None:
    if len({c.key for c in candidates}) != len(candidates):
        raise HTTPException(422, "Candidate keys must be unique")
    fragments = {f.locator: f.text for f in run.fragments}
    for candidate in candidates:
        if (
            candidate.locator not in fragments
            or not candidate.excerpt
            or candidate.excerpt not in fragments[candidate.locator]
        ):
            raise HTTPException(422, "Each candidate needs an exact source excerpt and locator")
        if not candidate.user_supplied:
            for field, value in candidate.data.items():
                if (
                    field
                    in {
                        "type",
                        "category",
                        "employment_type",
                        "importance",
                        "ordering_hint",
                        "verified_by_user",
                    }
                    or value is None
                ):
                    continue
                if field.endswith("_id"):
                    if not isinstance(value, str) or not value.startswith("@"):
                        raise HTTPException(
                            422, "Model parent links must reference staged candidates"
                        )
                    continue
                if field == "current":
                    if value and not any(
                        word in fragments[candidate.locator].casefold()
                        for word in ("present", "current")
                    ):
                        raise HTTPException(
                            422, "Current employment must be explicit in source text"
                        )
                    continue
                if field == "metric_value":
                    metric = str(value) + ("%" if candidate.data.get("metric_unit") == "%" else "")
                    if numbers(metric) - numbers(fragments[candidate.locator]):
                        raise HTTPException(422, "Extracted metric is absent from source text")
                values = value if isinstance(value, list) else [value]
                if any(
                    str(item)
                    and str(item).casefold() not in fragments[candidate.locator].casefold()
                    for item in values
                ):
                    raise HTTPException(
                        422,
                        "Extracted fact is absent from source text; supply it explicitly in review",
                    )


def review(
    db: Session,
    owner: UUID,
    identifier: UUID,
    data: Review,
    *,
    model_provenance: dict[str, str] | None = None,
) -> ImportRun:
    run = repository.get(db, owner, identifier)
    validate_candidates(run, data.candidates)
    candidates = []
    for candidate in data.candidates:
        # Confirmation explicitly marks edited field values as supplied by the user.
        values = candidate.model_copy(update={"duplicate_ids": []})
        kind = candidate.data.get("type")
        if kind in {"experience", "project", "education", "skill"}:
            for existing in career.list_records(db, owner, kind):
                for key in ("name", "company", "institution"):
                    if (
                        isinstance(candidate.data.get(key), str)
                        and candidate.data[key].casefold()
                        == str(getattr(existing.data, key, "")).casefold()
                    ):
                        values.duplicate_ids.append(existing.id)
                        break
        candidates.append(values)
    result = repository.change(
        db,
        owner,
        identifier,
        data.expected_revision,
        {
            "fragments": [f.model_dump() for f in run.fragments],
            "candidates": [c.model_dump(mode="json") for c in candidates],
            "saved_ids": [],
            "provenance": model_provenance if model_provenance is not None else run.provenance,
        },
    )
    db.commit()
    return result


async def extract(
    db: Session, owner: UUID, identifier: UUID, revision: int, gateway: Gateway
) -> ImportRun:
    run = repository.get(db, owner, identifier)
    if run.status != "review" or run.revision != revision:
        raise HTTPException(409, "Import changed; reload")
    endpoint, profile = settings.resolve(db, owner, "import_extraction")
    task_key = (owner, identifier)
    if task_key in ACTIVE:
        raise HTTPException(409, "Extraction already running; cancel or wait")
    task = asyncio.current_task()
    assert task is not None
    ACTIVE[task_key] = task
    try:
        output = await extract_import(gateway, endpoint, profile, run.fragments)
    except asyncio.CancelledError as error:
        raise HTTPException(409, "Extraction cancelled; no candidates saved") from error
    finally:
        ACTIVE.pop(task_key, None)
    validate_session(db)
    extracted = [
        Candidate(
            key=c.key,
            data=c.data.model_dump(mode="json", exclude_none=True),
            locator=c.locator,
            excerpt=c.excerpt,
        )
        for c in output.candidates
    ]
    validate_candidates(run, extracted)
    return review(
        db,
        owner,
        identifier,
        Review(
            expected_revision=revision,
            candidates=extracted,
        ),
        model_provenance=provenance("import_extraction", endpoint, profile),
    )


def commit(db: Session, owner: UUID, identifier: UUID, revision: int) -> ImportRun:
    run = repository.get(db, owner, identifier)
    if run.status == "committed":
        return run
    if run.revision != revision or run.status != "review":
        raise HTTPException(409, "Import changed; reload")
    accepted = [c for c in run.candidates if c.decision == "accepted"]
    if not accepted:
        raise HTTPException(422, "Accept at least one candidate first")
    ids: dict[str, UUID] = {}
    try:
        # Reserve review revision before writes; all facts and result commit together.
        repository.change(
            db,
            owner,
            identifier,
            revision,
            {
                "fragments": [f.model_dump() for f in run.fragments],
                "candidates": [c.model_dump(mode="json") for c in run.candidates],
                "saved_ids": [],
                "provenance": run.provenance,
            },
        )
        pending = list(accepted)
        # @candidate references are import-local keys, not database IDs. Save parents
        # first, then remap children; a stalled pass means an unresolved dependency.
        while pending:
            advanced = False
            for candidate in list(pending):
                values = dict(candidate.data)
                refs = {
                    k: v[1:]
                    for k, v in values.items()
                    if k.endswith("_id") and isinstance(v, str) and v.startswith("@")
                }
                if any(key not in ids for key in refs.values()):
                    continue
                values.update({key: str(ids[value]) for key, value in refs.items()})
                data = ADAPTER.validate_python(values)
                # User approval is required even for exact model extraction; no model fact
                # is treated as independently verified.
                record = career.save(db, owner, data, commit=False)
                ids[candidate.key] = record.id
                pending.remove(candidate)
                advanced = True
            if not advanced:
                raise HTTPException(
                    422,
                    "Missing, rejected or cyclic candidate parent; "
                    "accept parents or select existing record IDs",
                )
        result = repository.change(
            db,
            owner,
            identifier,
            revision + 1,
            {
                "fragments": [f.model_dump() for f in run.fragments],
                "candidates": [c.model_dump(mode="json") for c in run.candidates],
                "saved_ids": [str(i) for i in ids.values()],
                "provenance": run.provenance,
            },
            status="committed",
        )
        db.commit()
        return result
    except ValidationError as error:
        db.rollback()
        raise HTTPException(
            422, "Approved candidate has invalid career fields; correct the review"
        ) from error
    except BaseException:
        db.rollback()
        raise


def discard(db: Session, owner: UUID, identifier: UUID, revision: int) -> ImportRun:
    result = repository.change(
        db,
        owner,
        identifier,
        revision,
        {"fragments": [], "candidates": [], "saved_ids": []},
        status="discarded",
        clear_original=True,
    )
    db.commit()
    return result


def original(db: Session, owner: UUID, identifier: UUID) -> tuple[bytes, str]:
    encrypted, mime = repository.original(db, owner, identifier)
    try:
        content = AESGCM(upload_key()).decrypt(
            encrypted[:12], encrypted[12:], b"stonks.upload.v1:" + str(owner).encode()
        )
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            503, "Upload encryption key is wrong or retained file is corrupt"
        ) from error
    return content, mime
