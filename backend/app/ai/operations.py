"""Request-owned inference cancellation for Phase 6 workflows."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import HTTPException

ACTIVE: dict[tuple[UUID, UUID], asyncio.Task[object]] = {}


@asynccontextmanager
async def operation(owner: UUID, identifier: UUID) -> AsyncIterator[None]:
    key = (owner, identifier)
    if key in ACTIVE:
        raise HTTPException(409, "Operation already running; cancel or wait")
    task = asyncio.current_task()
    assert task is not None
    ACTIVE[key] = task
    try:
        yield
    except asyncio.CancelledError as error:
        raise HTTPException(409, "Operation cancelled; no new result saved") from error
    finally:
        ACTIVE.pop(key, None)


def cancel(owner: UUID, identifier: UUID) -> None:
    task = ACTIVE.get((owner, identifier))
    if task:
        task.cancel()


async def cancel_all() -> None:
    tasks = list(ACTIVE.values())
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
