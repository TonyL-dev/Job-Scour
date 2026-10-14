from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, inspect, select, update
from sqlalchemy.orm import Session

from app.importers.models import ImportRecord
from app.importers.schemas import ImportRun


def dto(row: ImportRecord) -> ImportRun:
    return ImportRun(
        id=row.id,
        filename=row.filename,
        revision=row.revision,
        status=row.status,
        original_available=row.original is not None,
        **row.payload,
    )


def get(db: Session, owner: UUID, identifier: UUID) -> ImportRun:
    row = db.scalar(
        select(ImportRecord).where(ImportRecord.user_id == owner, ImportRecord.id == identifier)
    )
    if row is None:
        raise HTTPException(404, "Import not found")
    return dto(row)


def list_runs(db: Session, owner: UUID) -> list[ImportRun]:
    return [
        dto(row)
        for row in db.scalars(
            select(ImportRecord)
            .where(ImportRecord.user_id == owner)
            .order_by(ImportRecord.created_at.desc())
            .limit(100)
        )
    ]


def create(
    db: Session,
    owner: UUID,
    filename: str,
    mime: str,
    payload: dict[str, object],
    original: bytes | None,
) -> ImportRun:
    count = (
        db.scalar(
            select(func.count())
            .select_from(ImportRecord)
            .where(ImportRecord.user_id == owner, ImportRecord.status.in_(["parsing", "review"]))
        )
        or 0
    )
    if count >= 10:
        raise HTTPException(429, "Finish or discard pending imports (limit 10)")
    row = ImportRecord(
        user_id=owner,
        filename=filename,
        mime=mime,
        payload=payload,
        original=original,
        status="parsing",
    )
    db.add(row)
    db.commit()
    return dto(row)


def change(
    db: Session,
    owner: UUID,
    identifier: UUID,
    revision: int,
    payload: dict[str, object],
    status: str = "review",
    clear_original: bool = False,
) -> ImportRun:
    values: dict[str, object] = {"payload": payload, "revision": revision + 1, "status": status}
    if clear_original:
        values["original"] = None
    changed = db.execute(
        update(ImportRecord)
        .where(
            ImportRecord.user_id == owner,
            ImportRecord.id == identifier,
            ImportRecord.revision == revision,
            ImportRecord.status == "review",
        )
        .values(**values)
    )
    if changed.rowcount != 1:  # type: ignore[attr-defined]
        raise HTTPException(409, "Import review changed; reload")
    return get(db, owner, identifier)


def original(db: Session, owner: UUID, identifier: UUID) -> tuple[bytes, str]:
    row = db.scalar(
        select(ImportRecord).where(ImportRecord.user_id == owner, ImportRecord.id == identifier)
    )
    if row is None or row.original is None:
        raise HTTPException(404, "Original upload unavailable")
    return row.original, row.mime


def remove_original(db: Session, owner: UUID, identifier: UUID) -> None:
    get(db, owner, identifier)
    db.execute(
        update(ImportRecord)
        .where(ImportRecord.user_id == owner, ImportRecord.id == identifier)
        .values(original=None)
    )
    db.commit()


def finish_parse(
    db: Session, owner: UUID, identifier: UUID, payload: dict[str, object], original: bytes | None
) -> ImportRun:
    result = db.execute(
        update(ImportRecord)
        .where(
            ImportRecord.user_id == owner,
            ImportRecord.id == identifier,
            ImportRecord.status == "parsing",
        )
        .values(status="review", payload=payload, original=original)
    )
    if result.rowcount != 1:  # type: ignore[attr-defined]
        raise HTTPException(409, "Parsing was cancelled or interrupted")
    db.commit()
    return get(db, owner, identifier)


def fail_parse(db: Session, owner: UUID, identifier: UUID, reason: str) -> None:
    db.execute(
        update(ImportRecord)
        .where(
            ImportRecord.user_id == owner,
            ImportRecord.id == identifier,
            ImportRecord.status == "parsing",
        )
        .values(
            status="failed",
            original=None,
            payload={"fragments": [], "candidates": [], "saved_ids": [], "error": reason},
        )
    )
    db.commit()


def recover_parsing(db: Session, owner: UUID | None = None) -> None:
    if not inspect(db.get_bind()).has_table("import_runs"):
        return
    query = update(ImportRecord).where(ImportRecord.status == "parsing")
    if owner:
        query = query.where(ImportRecord.user_id == owner)
    db.execute(
        query.values(
            status="failed",
            original=None,
            payload={
                "fragments": [],
                "candidates": [],
                "saved_ids": [],
                "error": "Parsing interrupted by restart or workspace privacy change; upload again",
            },
        )
    )
    db.commit()
