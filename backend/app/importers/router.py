from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Request, Response
from pydantic import Field

from app.auth.service import Database, Owner
from app.importers import service
from app.importers.schemas import ImportRun, Review, Upload

router = APIRouter(prefix="/api/imports", tags=["importers"])


@router.get("")
def list_runs(db: Database, owner: Owner) -> list[ImportRun]:
    return service.list_runs(db, owner)


@router.post("", status_code=201)
def upload(data: Upload, db: Database, owner: Owner) -> ImportRun:
    return service.upload(db, owner, data)


@router.get("/{identifier}")
def get(identifier: UUID, db: Database, owner: Owner) -> ImportRun:
    return service.get(db, owner, identifier)


@router.put("/{identifier}")
def review(identifier: UUID, data: Review, db: Database, owner: Owner) -> ImportRun:
    return service.review(db, owner, identifier, data)


@router.post("/{identifier}/extract")
async def extract(
    identifier: UUID,
    revision: Annotated[int, Field(ge=1)],
    request: Request,
    db: Database,
    owner: Owner,
) -> ImportRun:
    return await service.extract(db, owner, identifier, revision, request.app.state.gateway)


@router.post("/{identifier}/commit")
def commit(
    identifier: UUID, revision: Annotated[int, Field(ge=1)], db: Database, owner: Owner
) -> ImportRun:
    return service.commit(db, owner, identifier, revision)


@router.post("/{identifier}/discard")
def discard(
    identifier: UUID, revision: Annotated[int, Field(ge=1)], db: Database, owner: Owner
) -> ImportRun:
    return service.discard(db, owner, identifier, revision)


@router.get("/{identifier}/original")
def original(identifier: UUID, db: Database, owner: Owner) -> Response:
    content, mime = service.original(db, owner, identifier)
    return Response(
        content,
        media_type=mime,
        headers={"Content-Disposition": 'attachment; filename="original-upload"'},
    )


@router.delete("/{identifier}/original", status_code=204)
def delete_original(identifier: UUID, db: Database, owner: Owner) -> Response:
    service.remove_original(db, owner, identifier)
    return Response(status_code=204)


@router.post("/{identifier}/cancel", status_code=204)
async def cancel(identifier: UUID, db: Database, owner: Owner) -> Response:
    service.cancel(db, owner, identifier)
    return Response(status_code=204)
