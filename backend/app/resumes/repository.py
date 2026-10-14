import hashlib
import json
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.resumes.models import Resume, Version
from app.resumes.schemas import MasterResume, ResumeDocument, ResumeVersion, SaveResume


def find(session: Session, owner: UUID, identifier: UUID) -> Resume | None:
    return session.scalar(select(Resume).where(Resume.user_id == owner, Resume.id == identifier))


def read(session: Session, row: Resume) -> MasterResume:
    version = session.scalar(
        select(Version).where(
            Version.user_id == row.user_id,
            Version.document_id == row.id,
            Version.version_number == row.version_number,
        )
    )
    assert version is not None
    return MasterResume(
        id=row.id,
        title=row.title,
        gold_standard=row.gold_standard,
        version_number=row.version_number,
        updated_at=row.updated_at,
        content=ResumeDocument.model_validate(version.content_snapshot),
        kind=row.kind,
        parent_document_id=row.parent_document_id,
    )


def list_resumes(session: Session, owner: UUID) -> list[MasterResume]:
    return [
        read(session, row)
        for row in session.scalars(
            select(Resume).where(Resume.user_id == owner).order_by(Resume.updated_at.desc())
        )
    ]


def save(
    session: Session,
    owner: UUID,
    data: SaveResume,
    identifier: UUID | None,
    kind: str = "master",
    *,
    commit: bool = True,
    change_kind: str = "user",
    parent_document_id: UUID | None = None,
    restored_from_version_id: UUID | None = None,
) -> MasterResume | None:
    if data.gold_standard:
        session.execute(
            update(Resume)
            .where(Resume.user_id == owner, Resume.gold_standard.is_(True))
            .values(gold_standard=False)
        )
    if identifier:
        result = session.execute(
            update(Resume)
            .where(
                Resume.id == identifier,
                Resume.user_id == owner,
                Resume.version_number == data.expected_version,
            )
            .values(
                title=data.title,
                gold_standard=data.gold_standard,
                version_number=data.expected_version + 1,
            )
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            session.rollback()
            return None
        row = find(session, owner, identifier)
        assert row is not None
    else:
        row = Resume(
            user_id=owner,
            title=data.title,
            kind=kind,
            parent_document_id=parent_document_id,
            version_number=1,
            gold_standard=data.gold_standard,
        )
        session.add(row)
        session.flush()
    snapshot = data.content.model_dump(mode="json")
    digest = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    session.add(
        Version(
            user_id=owner,
            document_id=row.id,
            version_number=row.version_number,
            content_snapshot=snapshot,
            content_hash=digest,
            change_kind="autosave" if data.autosave else change_kind,
            restored_from_version_id=restored_from_version_id,
        )
    )
    if commit:
        session.commit()
        session.refresh(row)
    else:
        session.flush()
    return read(session, row)


def versions(session: Session, owner: UUID, identifier: UUID) -> list[ResumeVersion]:
    return [
        ResumeVersion(
            id=r.id,
            document_id=r.document_id,
            version_number=r.version_number,
            created_at=r.created_at,
            content=ResumeDocument.model_validate(r.content_snapshot),
            content_hash=r.content_hash,
            change_kind=r.change_kind,
            restored_from_version_id=r.restored_from_version_id,
        )
        for r in session.scalars(
            select(Version)
            .where(Version.user_id == owner, Version.document_id == identifier)
            .order_by(Version.version_number.desc())
        )
    ]


def version(session: Session, owner: UUID, identifier: UUID) -> ResumeVersion | None:
    r = session.scalar(select(Version).where(Version.user_id == owner, Version.id == identifier))
    return (
        ResumeVersion(
            id=r.id,
            document_id=r.document_id,
            version_number=r.version_number,
            created_at=r.created_at,
            content=ResumeDocument.model_validate(r.content_snapshot),
            content_hash=r.content_hash,
            change_kind=r.change_kind,
            restored_from_version_id=r.restored_from_version_id,
        )
        if r
        else None
    )
