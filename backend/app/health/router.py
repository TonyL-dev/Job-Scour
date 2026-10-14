from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.health.schemas import HealthResponse, LivenessResponse
from app.health.service import check_health

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health/live", response_model=LivenessResponse, operation_id="get_liveness")
def liveness() -> LivenessResponse:
    return LivenessResponse()


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "Database not ready"}},
    operation_id="get_health",
)
def health(
    request: Request, response: Response, session: Annotated[Session, Depends(get_session)]
) -> HealthResponse:
    result = check_health(session, request.app.state.settings)
    if result.status == "degraded":
        response.status_code = 503
    return result
