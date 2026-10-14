from uuid import UUID

from fastapi import APIRouter, Response

from app.auth.service import Database, Owner
from app.resumes.schemas import Preview
from app.templates import service
from app.templates.schemas import Asset, AssetUpload, CustomTemplate, TemplateSave

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("")
def templates(db: Database, owner: Owner) -> list[CustomTemplate]:
    return service.list_templates(db, owner)


@router.post("", status_code=201)
def create(data: TemplateSave, db: Database, owner: Owner) -> CustomTemplate:
    return service.save(db, owner, data)


@router.put("/{document_id}")
def edit(document_id: UUID, data: TemplateSave, db: Database, owner: Owner) -> CustomTemplate:
    return service.save(db, owner, data, document_id)


@router.delete("/{identifier}", status_code=204)
def retire(identifier: UUID, db: Database, owner: Owner) -> Response:
    service.retire(db, owner, identifier)
    return Response(status_code=204)


@router.post("/preview")
def preview(data: TemplateSave, db: Database, owner: Owner) -> Preview:
    return service.preview_example(db, owner, data)


@router.get("/assets")
def assets(db: Database, owner: Owner) -> list[Asset]:
    return service.list_assets(db, owner)


@router.post("/assets", status_code=201)
def upload(data: AssetUpload, db: Database, owner: Owner) -> Asset:
    return service.upload_asset(db, owner, data)
