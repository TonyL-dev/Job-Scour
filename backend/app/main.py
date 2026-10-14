from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from html import escape

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import HTMLResponse, JSONResponse, Response

from app.ai.gateway import Gateway
from app.applications.router import router as applications_router
from app.ats.router import router as ats_router
from app.auth.repository import LOCAL_OWNER
from app.career.router import router as career_router
from app.core.config import Settings, get_settings
from app.core.database import build_engine
from app.core.http import PrivateHTTP
from app.core.workspace import WorkspaceBarrier
from app.cover_letters.router import router as letters_router
from app.health.router import router
from app.importers.router import router as imports_router
from app.jobs.router import router as jobs_router
from app.privacy.repository import passcode, verify_store
from app.privacy.router import router as privacy_router
from app.privacy.service import LockState
from app.profile.router import router as profile_router
from app.prompt_management.router import router as prompts_router
from app.rendering.service import clear_cache
from app.resumes.generation_router import router as generation_router
from app.resumes.generation_service import RunManager
from app.resumes.router import router as resumes_router
from app.settings.router import router as settings_router
from app.templates.router import router as templates_router


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        clear_cache()
        application.state.engine = build_engine(config.database_url)
        try:
            with Session(application.state.engine) as db:
                verify_store(db)
                encoded = passcode(db, LOCAL_OWNER) if config.mode == "local" else None
                from app.cover_letters.repository import recover
                from app.importers.repository import recover_parsing

                recover(db)
                recover_parsing(db)
            application.state.barrier = WorkspaceBarrier()
            application.state.deleting = False
            application.state.lock = LockState(encoded)
            application.state.gateway = Gateway()
            application.state.runs = RunManager(
                application.state.engine, application.state.gateway, application.state.barrier
            )
            try:
                yield
            finally:
                from app.ai.operations import cancel_all as cancel_operations
                from app.importers.service import cancel_all

                await cancel_all()
                await cancel_operations()
                await application.state.runs.close()
        finally:
            clear_cache()
            application.state.engine.dispose()

    application = FastAPI(
        title=config.name, version="0.1.0", lifespan=lifespan, docs_url=None, redoc_url=None
    )
    application.state.settings = config
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.frontend_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )
    if config.mode == "local":
        application.add_middleware(
            TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"]
        )
    application.include_router(router)
    application.include_router(career_router)
    application.include_router(resumes_router)
    application.include_router(settings_router)
    application.include_router(jobs_router)
    application.include_router(imports_router)
    application.include_router(profile_router)
    application.include_router(letters_router)
    application.include_router(prompts_router)
    application.include_router(templates_router)
    application.include_router(generation_router)
    application.include_router(privacy_router)
    application.include_router(ats_router)
    application.include_router(applications_router)

    @application.get("/docs", response_class=HTMLResponse, include_in_schema=False)
    def local_api_reference() -> str:
        rows = []
        for path, operations in application.openapi()["paths"].items():
            for method, operation in operations.items():
                if method in {"get", "post", "put", "delete", "patch"}:
                    rows.append(
                        f"<tr><td>{escape(method.upper())}</td><td>{escape(path)}</td>"
                        f"<td>{escape(operation.get('summary', ''))}</td></tr>"
                    )
        return (
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>Local API reference</title><style>"
            "body{font-family:system-ui;margin:2rem}td,th{padding:.5rem;text-align:left}"
            "table{border-collapse:collapse}tr{border-bottom:1px solid #ddd}</style>"
            '<h1>Local API reference</h1><p><a href="/openapi.json">OpenAPI schema</a></p>'
            "<table><thead><tr><th>Method</th><th>Path</th><th>Operation</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></html>"
        )

    @application.middleware("http")
    async def private_workspace(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if (
            request.app.state.deleting
            and request.url.path.startswith("/api/")
            and request.url.path not in {"/api/health", "/api/health/live", "/api/privacy/status"}
        ):
            return JSONResponse(
                {"detail": "Workspace deletion in progress"},
                status_code=409,
                headers={"Cache-Control": "no-store"},
            )
        epoch = request.app.state.barrier.epoch
        origin = request.headers.get("origin")
        if (
            request.method in {"POST", "PUT", "DELETE"}
            and origin
            and origin not in config.frontend_origins
        ):
            return JSONResponse({"detail": "Untrusted request origin"}, status_code=403)
        if (
            request.url.path.startswith("/api/")
            and request.url.path
            not in {
                "/api/health",
                "/api/health/live",
                "/api/health/ready",
                "/api/privacy/status",
                "/api/privacy/unlock",
            }
            and not request.app.state.lock.unlocked(request.cookies.get("stonks_session"))
        ):
            return JSONResponse(
                {"detail": "Workspace locked. Unlock with your passcode."},
                status_code=423,
                headers={"Cache-Control": "no-store"},
            )
        if config.mode != "local" and request.url.path.startswith("/api/privacy"):
            return JSONResponse({"detail": "Privacy controls require local mode"}, status_code=403)
        response = await call_next(request)
        if (
            request.url.path.startswith("/api/")
            and request.url.path
            not in {
                "/api/health",
                "/api/health/live",
                "/api/privacy/status",
                "/api/privacy/unlock",
                "/api/privacy/passcode",
                "/api/privacy/lock",
                "/api/privacy/delete-all",
            }
            and epoch != request.app.state.barrier.epoch
        ):
            return JSONResponse(
                {"detail": "Workspace access changed. Unlock or reload."},
                status_code=423,
                headers={"Cache-Control": "no-store"},
            )
        response.headers["Cache-Control"] = "no-store"
        return response

    application.add_middleware(PrivateHTTP)

    return application


app = create_app()
