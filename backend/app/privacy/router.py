from fastapi import APIRouter, Request, Response

from app.auth.service import Database, Owner
from app.privacy import service
from app.privacy.schemas import DeleteInput, PasscodeInput, PrivacyStatus, UnlockInput

router = APIRouter(prefix="/api/privacy", tags=["privacy"])
COOKIE = "stonks_session"


def cookie(response: Response, token: str, request: Request) -> None:
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
        max_age=1800,
        path="/",
    )


@router.get("/status")
def status(request: Request) -> PrivacyStatus:
    return service.status(request.app.state.lock, request.cookies.get(COOKIE))


@router.post("/unlock")
def unlock(data: UnlockInput, request: Request, response: Response) -> PrivacyStatus:
    token = request.app.state.lock.unlock(data.passcode)
    cookie(response, token, request)
    return service.status(request.app.state.lock, token)


@router.post("/passcode")
async def configure(
    data: PasscodeInput, request: Request, response: Response, session: Database, owner: Owner
) -> PrivacyStatus:
    token = service.configure(
        session,
        owner,
        request.app.state.lock,
        data.passcode,
        data.current_passcode,
        request.app.state.barrier,
    )
    await service.cancel_pending(request.app.state)
    cookie(response, token, request)
    return service.status(request.app.state.lock, token)


@router.post("/lock")
async def lock(request: Request, response: Response, owner: Owner) -> PrivacyStatus:
    await service.lock_workspace(request.app.state)
    response.delete_cookie(COOKIE, path="/")
    return service.status(request.app.state.lock, None)


@router.get("/export")
def export(session: Database, owner: Owner) -> dict[str, object]:
    return service.export(session, owner)


@router.post("/delete-all", status_code=204)
async def delete_all(
    data: DeleteInput, request: Request, session: Database, owner: Owner
) -> Response:
    await service.delete_workspace(session, owner, request.app.state, data.confirmation)
    return Response(status_code=204)


@router.get(
    "/export/archive",
    response_class=Response,
    responses={
        200: {"content": {"application/zip": {"schema": {"type": "string", "format": "binary"}}}}
    },
)
def archive(session: Database, owner: Owner) -> Response:
    return Response(
        service.archive(session, owner),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="stonks-export.zip"',
            "Cache-Control": "no-store",
        },
    )
