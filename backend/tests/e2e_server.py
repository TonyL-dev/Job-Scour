"""Disposable browser fixture server. Never used by the product entry point."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient
from phase6_fixtures import phase6_transport
from test_phase3 import setup

from app.ai.gateway import Gateway
from app.main import create_app

app = create_app()
original = app.router.lifespan_context


@asynccontextmanager
async def fixture_lifespan(application: FastAPI) -> AsyncIterator[None]:
    async with original(application):
        gateway = Gateway(phase6_transport())
        application.state.gateway = gateway
        application.state.runs.gateway = gateway
        yield


app.router.lifespan_context = fixture_lifespan

if __name__ == "__main__":
    with TestClient(app) as seed:
        setup(seed)
        profile = seed.get("/api/settings").json()["profiles"][0]["id"]
        for task in ("import_extraction", "profile_questions", "cover_letter"):
            seed.put("/api/settings/assignments", json={"task": task, "profile_id": profile})
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ["E2E_BACKEND_PORT"]))
