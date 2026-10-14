import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import suppress
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.ai.gateway import get_gateway as gateway
from app.auth.service import Database, Owner
from app.core.workspace import validate_session
from app.jobs import schemas, service
from app.jobs.schemas import AnalysisResult, AnalyzeInput, Job, JobInput, PromptInfo

router = APIRouter(prefix="/api/jobs", tags=["Job analysis"])


@router.get("", response_model=list[Job])
def list_jobs(owner: Owner, db: Database) -> list[Job]:
    return service.list_jobs(db, owner)


@router.post("", response_model=Job, status_code=201)
def create(data: JobInput, owner: Owner, db: Database) -> Job:
    return service.create(db, owner, data)


@router.get("/prompts", response_model=list[PromptInfo])
def prompts(owner: Owner, db: Database) -> list[PromptInfo]:
    return service.prompts(db, owner)


@router.get("/analyses")
def analyses(owner: Owner, db: Database) -> list[schemas.AnalysisChoice]:
    return service.analyses(db, owner)


@router.get("/{identifier}", response_model=Job)
def get(identifier: UUID, owner: Owner, db: Database) -> Job:
    return service.get(db, owner, identifier)


@router.post("/{identifier}/analyze", response_model=AnalysisResult)
async def analyze(
    identifier: UUID, data: AnalyzeInput, owner: Owner, db: Database, request: Request
) -> AnalysisResult:
    task = asyncio.create_task(
        service.analyze(db, owner, identifier, gateway(request), data.use_embeddings)
    )
    try:
        while not task.done():
            if await request.is_disconnected():
                raise HTTPException(499, "Analysis cancelled by the caller")
            await asyncio.wait({task}, timeout=0.2)
        return await task
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


@router.post("/{identifier}/analyze/stream", response_class=StreamingResponse)
async def stream(
    identifier: UUID, data: AnalyzeInput, owner: Owner, db: Database, request: Request
) -> StreamingResponse:
    service.get(db, owner, identifier)

    # HTTP/SSE lifetime owns the task; disconnect closes the gateway request.
    async def events() -> AsyncIterator[str]:
        queue: asyncio.Queue[tuple[str, object]] = asyncio.Queue(maxsize=8)
        last = ""

        async def progress(stage: str) -> None:
            nonlocal last
            if stage != last:
                await queue.put(("progress", {"stage": stage}))
                last = stage

        async def run() -> None:
            try:
                result = await service.analyze(
                    db, owner, identifier, gateway(request), data.use_embeddings, progress
                )
                await queue.put(("result", result.model_dump(mode="json")))
            except HTTPException as error:
                await queue.put(("error", {"detail": error.detail}))
            except TimeoutError:
                await queue.put(
                    (
                        "error",
                        {
                            "detail": "Model request timed out. "
                            "Retry with a smaller input or faster model."
                        },
                    )
                )
            except Exception:
                await queue.put(("error", {"detail": "Analysis failed. Retry the saved job."}))

        task = asyncio.create_task(run())
        try:
            while True:
                try:
                    validate_session(db)
                except HTTPException:
                    return
                try:
                    event, payload = await asyncio.wait_for(queue.get(), timeout=10)
                except TimeoutError:
                    if task.done():
                        await task
                        break
                    yield ": heartbeat\n\n"
                    continue
                try:
                    validate_session(db)
                except HTTPException:
                    return
                yield f"event: {event}\ndata: {json.dumps(payload)}\n\n"
                if event in {"error", "result"}:
                    break
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    return StreamingResponse(
        events(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"}
    )
