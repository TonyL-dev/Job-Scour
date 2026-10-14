from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.applications import repository as repo
from app.applications.schemas import Application, ApplicationEvent, ApplicationSave, EventInput
from app.jobs import service as jobs
from app.resumes import service as resumes


def get(db: Session, owner: UUID, identifier: UUID) -> Application:
    result = repo.get(db, owner, identifier)
    if result is None:
        raise HTTPException(404, "Application not found")
    return result


def list_all(db: Session, owner: UUID) -> list[Application]:
    return repo.list_all(db, owner)


def save(
    db: Session, owner: UUID, data: ApplicationSave, identifier: UUID | None = None
) -> Application:
    resumes.get_version(db, owner, data.version_id)
    if data.cover_letter_version_id:
        from app.cover_letters import service as letters

        letter = letters.get_version(db, owner, data.cover_letter_version_id)
        if data.job_id and letter.job_id != data.job_id:
            raise HTTPException(422, "Cover letter must match the application job")
    if data.job_id:
        jobs.get(db, owner, data.job_id)
    if identifier:
        get(db, owner, identifier)
    elif data.expected_revision != 0:
        raise HTTPException(409, "New applications require revision zero")
    result = repo.save(db, owner, data, identifier)
    if result is None:
        raise HTTPException(409, "Application changed elsewhere. Reload before saving.")
    return result


def events(db: Session, owner: UUID, identifier: UUID) -> list[ApplicationEvent]:
    get(db, owner, identifier)
    return repo.events(db, owner, identifier)


def event(db: Session, owner: UUID, identifier: UUID, data: EventInput) -> Application:
    get(db, owner, identifier)
    result = repo.event(db, owner, identifier, data)
    if result is None:
        raise HTTPException(409, "Application changed elsewhere. Reload before saving.")
    return result
