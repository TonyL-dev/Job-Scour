from uuid import UUID

from fastapi import APIRouter

from app.ats import service
from app.ats.schemas import Report, ReportInput
from app.auth.service import Database, Owner

router = APIRouter(prefix="/api/ats", tags=["ats"])


@router.post("/reports", status_code=201)
def create(data: ReportInput, session: Database, owner: Owner) -> Report:
    return service.create(session, owner, data)


@router.get("/reports/{version_id}")
def reports(version_id: UUID, session: Database, owner: Owner) -> list[Report]:
    return service.list_reports(session, owner, version_id)
