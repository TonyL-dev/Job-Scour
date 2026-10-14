from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.auth.service import Database, Owner
from app.resumes import generation_service as service
from app.resumes.generation_schemas import CommitReview, GenerateInput, GenerationRun, ReviewInput
from app.resumes.schemas import MasterResume, Preview

router = APIRouter(prefix="/api/generation", tags=["Generation and review"])


@router.get("")
def list_runs(db: Database, owner: Owner) -> list[GenerationRun]:
    return service.list_runs(db, owner)


@router.post("", status_code=202)
async def start(data: GenerateInput, db: Database, owner: Owner, request: Request) -> GenerationRun:
    return request.app.state.runs.start(db, owner, data)  # type: ignore[no-any-return]


@router.get("/{identifier}")
def get(identifier: UUID, db: Database, owner: Owner) -> GenerationRun:
    return service.get(db, owner, identifier)


@router.post("/{identifier}/cancel")
async def cancel(identifier: UUID, db: Database, owner: Owner, request: Request) -> GenerationRun:
    return await request.app.state.runs.cancel(db, owner, identifier)  # type: ignore[no-any-return]


@router.get("/{identifier}/events", response_class=StreamingResponse)
def events(
    identifier: UUID, db: Database, owner: Owner, request: Request, after: int = 0
) -> StreamingResponse:
    service.get(db, owner, identifier)
    return StreamingResponse(
        service.events(
            request.app.state.engine,
            owner,
            identifier,
            after,
            request.app.state.barrier,
            db.info["workspace_epoch"],
        ),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},
    )


@router.put("/{identifier}/review")
def review(identifier: UUID, data: ReviewInput, db: Database, owner: Owner) -> GenerationRun:
    return service.save_review(db, owner, identifier, data)


@router.post("/{identifier}/preview")
async def preview(identifier: UUID, data: ReviewInput, db: Database, owner: Owner) -> Preview:
    return await service.preview(db, owner, identifier, data)


@router.post("/{identifier}/commit", status_code=201)
def commit(identifier: UUID, data: CommitReview, db: Database, owner: Owner) -> MasterResume:
    return service.commit(db, owner, identifier, data)
