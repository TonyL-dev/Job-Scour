from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ats.models import ATSReport
from app.ats.schemas import Report
from app.jobs.models import AnalysisRecord
from app.jobs.schemas import JobAnalysis


def analysis(db: Session, owner: UUID, identifier: UUID) -> JobAnalysis | None:
    row = db.scalar(
        select(AnalysisRecord).where(
            AnalysisRecord.user_id == owner, AnalysisRecord.id == identifier
        )
    )
    return JobAnalysis.model_validate(row.result) if row else None


def save(db: Session, owner: UUID, report: Report) -> Report:
    db.add(
        ATSReport(
            id=report.id,
            user_id=owner,
            version_id=report.version_id,
            analysis_id=report.analysis_id,
            engine_version=report.engine_version,
            result=report.model_dump(mode="json"),
        )
    )
    db.commit()
    return report


def list_reports(db: Session, owner: UUID, version_id: UUID) -> list[Report]:
    return [
        Report.model_validate(r.result)
        for r in db.scalars(
            select(ATSReport)
            .where(ATSReport.user_id == owner, ATSReport.version_id == version_id)
            .order_by(ATSReport.created_at.desc())
        )
    ]
