from uuid import UUID

from fastapi import APIRouter, Request

from app.ai.gateway import get_gateway as gateway
from app.auth.service import Database, Owner
from app.settings import service
from app.settings.schemas import (
    Assignment,
    ConnectionResult,
    Detection,
    Endpoint,
    EndpointInput,
    ModelList,
    Profile,
    ProfileInput,
    WorkspaceSettings,
)

router = APIRouter(prefix="/api/settings", tags=["AI settings"])


@router.get("", response_model=WorkspaceSettings)
def read(owner: Owner, db: Database) -> WorkspaceSettings:
    return service.read(db, owner)


@router.post("/detect", response_model=list[Detection])
async def detect(owner: Owner, request: Request) -> list[Detection]:
    return await gateway(request).detect()


@router.post("/endpoints", response_model=Endpoint, status_code=201)
def save_endpoint(data: EndpointInput, owner: Owner, db: Database) -> Endpoint:
    return service.save_endpoint(db, owner, data)


@router.put("/endpoints/{identifier}", response_model=Endpoint)
def edit_endpoint(
    identifier: UUID, data: EndpointInput, owner: Owner, db: Database, request: Request
) -> Endpoint:
    saved = service.save_endpoint(db, owner, data, identifier)
    gateway(request).configure(saved)
    return saved


@router.post("/endpoints/{identifier}/models", response_model=ModelList)
async def models(identifier: UUID, owner: Owner, db: Database, request: Request) -> ModelList:
    return ModelList(models=await gateway(request).models(service.endpoint(db, owner, identifier)))


@router.post("/profiles", response_model=Profile, status_code=201)
def save_profile(data: ProfileInput, owner: Owner, db: Database) -> Profile:
    return service.save_profile(db, owner, data)


@router.put("/assignments", response_model=Assignment)
def assign(data: Assignment, owner: Owner, db: Database) -> Assignment:
    return service.assign(db, owner, data)


@router.post("/profiles/{identifier}/test", response_model=ConnectionResult)
async def test(identifier: UUID, owner: Owner, db: Database, request: Request) -> ConnectionResult:
    return await service.test_profile(db, owner, identifier, gateway(request))
