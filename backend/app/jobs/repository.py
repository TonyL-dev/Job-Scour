from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.jobs.models import AnalysisRecord, JobDescription, MatchRecord
from app.jobs.schemas import AnalysisChoice, Job, JobAnalysis, JobInput, MatchAnalysis


@dataclass(frozen=True)
class StoredAnalysis:
    id: UUID
    model: str
    prompt_version: str
    analysis: JobAnalysis


def snapshot(row: AnalysisRecord) -> StoredAnalysis:
    return StoredAnalysis(
        row.id, row.model, row.prompt_version, JobAnalysis.model_validate(row.result)
    )


def job(row: JobDescription) -> Job:
    return Job.model_validate({key: getattr(row, key) for key in Job.model_fields})


def create(db: Session, owner: UUID, data: JobInput) -> Job:
    row = JobDescription(user_id=owner, **data.model_dump())
    db.add(row)
    db.commit()
    return job(row)


def get_analysis(db: Session, owner: UUID, identifier: UUID) -> tuple[UUID, JobAnalysis] | None:
    row = db.scalar(
        select(AnalysisRecord).where(
            AnalysisRecord.user_id == owner, AnalysisRecord.id == identifier
        )
    )
    return (row.job_id, JobAnalysis.model_validate(row.result)) if row else None


def list_jobs(db: Session, owner: UUID) -> list[Job]:
    return [
        job(r)
        for r in db.scalars(
            select(JobDescription)
            .where(JobDescription.user_id == owner)
            .order_by(JobDescription.created_at.desc())
        )
    ]


def find(db: Session, owner: UUID, identifier: UUID) -> Job | None:
    row = db.scalar(
        select(JobDescription).where(
            JobDescription.user_id == owner, JobDescription.id == identifier
        )
    )
    return job(row) if row else None


def cached(db: Session, owner: UUID, identifier: UUID, fingerprint: str) -> StoredAnalysis | None:
    row = db.scalar(
        select(AnalysisRecord)
        .where(
            AnalysisRecord.user_id == owner,
            AnalysisRecord.job_id == identifier,
            AnalysisRecord.fingerprint == fingerprint,
        )
        .order_by(AnalysisRecord.created_at.desc())
        .limit(1)
    )
    return snapshot(row) if row else None


def save_analysis(
    db: Session,
    owner: UUID,
    job_id: UUID,
    fingerprint: str,
    model: str,
    prompt: str,
    analysis: JobAnalysis,
) -> StoredAnalysis:
    row = AnalysisRecord(
        user_id=owner,
        job_id=job_id,
        fingerprint=fingerprint,
        model=model,
        prompt_version=prompt,
        result=analysis.model_dump(mode="json"),
    )
    db.add(row)
    db.commit()
    return snapshot(row)


def save_match(
    db: Session, owner: UUID, identifier: UUID, match: MatchAnalysis, cached: bool
) -> None:
    db.add(
        MatchRecord(
            user_id=owner,
            analysis_id=identifier,
            result=match.model_dump(mode="json"),
            cached=cached,
        )
    )
    db.commit()


def analyses(db: Session, owner: UUID) -> list[AnalysisChoice]:
    rows = db.execute(
        select(
            AnalysisRecord.id,
            AnalysisRecord.job_id,
            JobDescription.company,
            JobDescription.title,
            AnalysisRecord.created_at,
        )
        .join(
            JobDescription,
            (JobDescription.id == AnalysisRecord.job_id)
            & (JobDescription.user_id == AnalysisRecord.user_id),
        )
        .where(AnalysisRecord.user_id == owner)
        .order_by(AnalysisRecord.created_at.desc())
    )
    return [AnalysisChoice.model_validate(dict(r)) for r in rows.mappings()]
