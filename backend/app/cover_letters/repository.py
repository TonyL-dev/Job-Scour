from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import inspect, select, update
from sqlalchemy.orm import Session

from app.cover_letters.models import LetterDocument, LetterOperation, LetterSnapshot
from app.cover_letters.schemas import LetterRun, LetterVersion


def run_dto(row: LetterOperation) -> LetterRun:
    return LetterRun(
        id=row.id,
        revision=row.revision,
        status=row.status,
        saved_version_id=row.saved_version_id,
        **row.payload,
    )


def get_run(db: Session, owner: UUID, identifier: UUID) -> LetterRun:
    row = db.scalar(
        select(LetterOperation).where(
            LetterOperation.user_id == owner, LetterOperation.id == identifier
        )
    )
    if row is None:
        raise HTTPException(404, "Cover letter run not found")
    return run_dto(row)


def list_runs(db: Session, owner: UUID) -> list[LetterRun]:
    return [
        run_dto(r)
        for r in db.scalars(
            select(LetterOperation)
            .where(LetterOperation.user_id == owner)
            .order_by(LetterOperation.created_at.desc())
            .limit(100)
        )
    ]


def create_run(db: Session, owner: UUID, payload: dict[str, object]) -> LetterRun:
    row = LetterOperation(user_id=owner, payload=payload)
    db.add(row)
    db.commit()
    return run_dto(row)


def change_run(
    db: Session,
    owner: UUID,
    run: LetterRun,
    payload: dict[str, object],
    status: str,
    saved: UUID | None = None,
) -> LetterRun:
    result = db.execute(
        update(LetterOperation)
        .where(
            LetterOperation.user_id == owner,
            LetterOperation.id == run.id,
            LetterOperation.revision == run.revision,
            LetterOperation.status == run.status,
        )
        .values(payload=payload, revision=run.revision + 1, status=status, saved_version_id=saved)
    )
    if result.rowcount != 1:  # type: ignore[attr-defined]
        raise HTTPException(409, "Cover letter review changed; reload")
    return get_run(db, owner, run.id)


def get_version(db: Session, owner: UUID, identifier: UUID) -> LetterVersion:
    row = db.scalar(
        select(LetterSnapshot).where(
            LetterSnapshot.user_id == owner, LetterSnapshot.id == identifier
        )
    )
    if row is None:
        raise HTTPException(404, "Cover letter version not found")
    return LetterVersion(
        id=row.id, document_id=row.document_id, version_number=row.version_number, **row.payload
    )


def list_versions(db: Session, owner: UUID) -> list[LetterVersion]:
    return [
        get_version(db, owner, r.id)
        for r in db.scalars(
            select(LetterSnapshot)
            .where(LetterSnapshot.user_id == owner)
            .order_by(LetterSnapshot.created_at.desc())
        )
    ]


def save_version(
    db: Session,
    owner: UUID,
    payload: dict[str, object],
    document_id: UUID | None = None,
    expected: int = 0,
) -> LetterVersion:
    if document_id is None:
        doc = LetterDocument(
            user_id=owner, title=payload["title"], job_id=UUID(str(payload["job_id"]))
        )
        db.add(doc)
        db.flush()
        document_id = doc.id
        number = 1
    else:
        result = db.execute(
            update(LetterDocument)
            .where(
                LetterDocument.user_id == owner,
                LetterDocument.id == document_id,
                LetterDocument.latest_version == expected,
            )
            .values(latest_version=expected + 1)
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise HTTPException(409, "Letter changed; reload its latest version")
        number = expected + 1
    row = LetterSnapshot(
        user_id=owner, document_id=document_id, version_number=number, payload=payload
    )
    db.add(row)
    db.flush()
    return get_version(db, owner, row.id)


def recover(db: Session) -> None:
    if not inspect(db.get_bind()).has_table("cover_letter_runs"):
        return
    for row in db.scalars(
        select(LetterOperation).where(LetterOperation.status.in_(["queued", "running"]))
    ):
        row.status = "failed"
        row.revision += 1
        row.payload = {**row.payload, "error": "Interrupted by backend restart; start a new run"}
    db.commit()


def cancel_pending(db: Session, owner: UUID) -> None:
    if not inspect(db.get_bind()).has_table("cover_letter_runs"):
        return
    for row in db.scalars(
        select(LetterOperation).where(
            LetterOperation.user_id == owner, LetterOperation.status.in_(["queued", "running"])
        )
    ):
        row.status = "cancelled"
        row.revision += 1
        row.payload = {**row.payload, "error": "Cancelled by workspace privacy change"}
    db.commit()
