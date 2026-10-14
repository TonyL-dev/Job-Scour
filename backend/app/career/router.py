from uuid import UUID

from fastapi import APIRouter, Response

from app.auth.service import Database, Owner
from app.career import service
from app.career.schemas import CareerForm, CareerInput, CareerRecord, CareerType

router = APIRouter(prefix="/api/career", tags=["career"])


@router.get("/forms")
def forms(owner: Owner) -> list[CareerForm]:
    return service.forms()


@router.get("/{kind}")
def list_records(kind: CareerType, session: Database, owner: Owner) -> list[CareerRecord]:
    return service.list_records(session, owner, kind)


@router.post("", status_code=201)
def create(data: CareerInput, session: Database, owner: Owner) -> CareerRecord:
    return service.save(session, owner, data)


@router.get("/{kind}/{identifier}")
def get(kind: CareerType, identifier: UUID, session: Database, owner: Owner) -> CareerRecord:
    return service.get(session, owner, kind, identifier)


@router.put("/{identifier}")
def update(identifier: UUID, data: CareerInput, session: Database, owner: Owner) -> CareerRecord:
    return service.save(session, owner, data, identifier)


@router.delete("/{kind}/{identifier}", status_code=204)
def retire(kind: CareerType, identifier: UUID, session: Database, owner: Owner) -> Response:
    service.retire(session, owner, kind, identifier)
    return Response(status_code=204)
