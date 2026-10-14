from datetime import date
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.applications.models import ApplicationRecord, EventRecord
from app.applications.schemas import Application, ApplicationEvent, ApplicationSave, EventInput
from app.resumes.models import Version


def dto(db: Session, row: ApplicationRecord) -> Application:
    version = db.execute(
        select(Version.document_id, Version.version_number).where(
            Version.id == row.version_id, Version.user_id == row.user_id
        )
    ).one()
    return Application.model_validate(
        {
            **{
                k: getattr(row, k)
                for k in Application.model_fields
                if k not in {"document_id", "version_number"}
            },
            "document_id": version.document_id,
            "version_number": version.version_number,
        }
    )


def get(db: Session, owner: UUID, identifier: UUID) -> Application | None:
    row = db.scalar(
        select(ApplicationRecord).where(
            ApplicationRecord.user_id == owner, ApplicationRecord.id == identifier
        )
    )
    return dto(db, row) if row else None


def list_all(db: Session, owner: UUID) -> list[Application]:
    return [
        dto(db, r)
        for r in db.scalars(
            select(ApplicationRecord)
            .where(ApplicationRecord.user_id == owner)
            .order_by(ApplicationRecord.updated_at.desc())
        )
    ]


def save(
    db: Session, owner: UUID, data: ApplicationSave, identifier: UUID | None
) -> Application | None:
    values = data.model_dump(exclude={"expected_revision"})
    previous = get(db, owner, identifier) if identifier else None
    if identifier:
        result = db.execute(
            update(ApplicationRecord)
            .where(
                ApplicationRecord.user_id == owner,
                ApplicationRecord.id == identifier,
                ApplicationRecord.revision == data.expected_revision,
            )
            .values(**values, revision=data.expected_revision + 1)
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            db.rollback()
            return None
    else:
        row = ApplicationRecord(user_id=owner, **values)
        db.add(row)
        db.flush()
        identifier = row.id
    if previous is None or previous.stage != data.stage:
        db.add(
            EventRecord(
                user_id=owner,
                application_id=identifier,
                stage=data.stage,
                date=data.date_applied or date.today(),
                notes="Stage saved",
            )
        )
    db.commit()
    return get(db, owner, identifier)


def events(db: Session, owner: UUID, identifier: UUID) -> list[ApplicationEvent]:
    return [
        ApplicationEvent.model_validate({k: getattr(r, k) for k in ApplicationEvent.model_fields})
        for r in db.scalars(
            select(EventRecord)
            .where(EventRecord.user_id == owner, EventRecord.application_id == identifier)
            .order_by(EventRecord.date, EventRecord.created_at)
        )
    ]


def event(db: Session, owner: UUID, identifier: UUID, data: EventInput) -> Application | None:
    result = db.execute(
        update(ApplicationRecord)
        .where(
            ApplicationRecord.user_id == owner,
            ApplicationRecord.id == identifier,
            ApplicationRecord.revision == data.expected_revision,
        )
        .values(stage=data.stage, revision=data.expected_revision + 1)
    )
    if result.rowcount != 1:  # type: ignore[attr-defined]
        db.rollback()
        return None
    db.add(
        EventRecord(
            user_id=owner,
            application_id=identifier,
            stage=data.stage,
            date=data.date,
            notes=data.notes,
        )
    )
    db.commit()
    return get(db, owner, identifier)
