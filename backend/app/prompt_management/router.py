from uuid import UUID

from fastapi import APIRouter, Request, Response

from app.ai.operations import cancel
from app.auth.service import Database, Owner
from app.prompt_management import service
from app.prompt_management.schemas import (
    Activation,
    CustomPrompt,
    EvaluationReport,
    PromptFork,
    Reset,
)

router = APIRouter(prefix="/api/prompts", tags=["prompt_management"])


@router.get("")
def prompts(db: Database, owner: Owner) -> list[CustomPrompt]:
    return service.list_prompts(db, owner)


@router.post("", status_code=201)
def fork(data: PromptFork, db: Database, owner: Owner) -> CustomPrompt:
    return service.fork(db, owner, data)


@router.get("/active")
def active(db: Database, owner: Owner) -> dict[str, UUID]:
    return service.active_ids(db, owner)


@router.post("/active")
def activate(data: Activation, db: Database, owner: Owner) -> dict[str, UUID]:
    return service.activate(db, owner, data)


@router.post("/reset")
def reset(data: Reset, db: Database, owner: Owner) -> dict[str, UUID]:
    return service.reset(db, owner, data)


@router.post("/{identifier}/evaluate")
async def evaluate(
    identifier: UUID, request: Request, db: Database, owner: Owner
) -> EvaluationReport:
    return await service.evaluate(db, owner, identifier, request.app.state.gateway)


@router.get("/reports/{identifier}")
def report(identifier: UUID, db: Database, owner: Owner) -> EvaluationReport:
    return service.get_report(db, owner, identifier)


@router.get("/{identifier}/reports")
def reports(identifier: UUID, db: Database, owner: Owner) -> list[EvaluationReport]:
    return service.reports(db, owner, identifier)


@router.post("/{identifier}/cancel", status_code=204)
async def cancel_evaluation(identifier: UUID, owner: Owner) -> Response:
    cancel(owner, identifier)
    return Response(status_code=204)
