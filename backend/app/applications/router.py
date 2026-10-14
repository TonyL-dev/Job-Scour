from uuid import UUID

from fastapi import APIRouter

from app.applications import service
from app.applications.schemas import Application, ApplicationEvent, ApplicationSave, EventInput
from app.auth.service import Database, Owner

router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.get("")
def list_all(session: Database, owner: Owner) -> list[Application]:
    return service.list_all(session, owner)


@router.post("", status_code=201)
def create(data: ApplicationSave, session: Database, owner: Owner) -> Application:
    return service.save(session, owner, data)


@router.put("/{identifier}")
def save(identifier: UUID, data: ApplicationSave, session: Database, owner: Owner) -> Application:
    return service.save(session, owner, data, identifier)


@router.get("/{identifier}/events")
def events(identifier: UUID, session: Database, owner: Owner) -> list[ApplicationEvent]:
    return service.events(session, owner, identifier)


@router.post("/{identifier}/events")
def event(identifier: UUID, data: EventInput, session: Database, owner: Owner) -> Application:
    return service.event(session, owner, identifier, data)
