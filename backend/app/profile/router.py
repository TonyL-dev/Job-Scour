from uuid import UUID

from fastapi import APIRouter, Request, Response

from app.ai.operations import cancel
from app.auth.service import Database, Owner
from app.profile import service
from app.profile.schemas import Answers, Confirm, ProfileReview, Start

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("")
def list_reviews(db: Database, owner: Owner) -> list[ProfileReview]:
    return service.list_reviews(db, owner)


@router.post("", status_code=201)
async def start(data: Start, request: Request, db: Database, owner: Owner) -> ProfileReview:
    return await service.start(db, owner, data, request.app.state.gateway)


@router.put("/{identifier}/answers")
def answers(identifier: UUID, data: Answers, db: Database, owner: Owner) -> ProfileReview:
    return service.answer(db, owner, identifier, data)


@router.post("/{identifier}/confirm")
def confirm(identifier: UUID, data: Confirm, db: Database, owner: Owner) -> ProfileReview:
    return service.confirm(db, owner, identifier, data)


@router.post("/{identifier}/discard")
def discard(identifier: UUID, revision: int, db: Database, owner: Owner) -> ProfileReview:
    return service.discard(db, owner, identifier, revision)


@router.post("/{source_id}/cancel", status_code=204)
async def cancel_questions(source_id: UUID, owner: Owner) -> Response:
    cancel(owner, source_id)
    return Response(status_code=204)
