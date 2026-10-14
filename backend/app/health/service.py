from sqlalchemy.orm import Session

from app.core.config import Settings
from app.health.repository import database_ready
from app.health.schemas import HealthResponse


def check_health(session: Session, settings: Settings) -> HealthResponse:
    ready = database_ready(session)
    return HealthResponse(
        status="ok" if ready else "degraded",
        service=settings.name,
        version="0.1.0",
        mode=settings.mode,
        database="ready" if ready else "unavailable",
    )
