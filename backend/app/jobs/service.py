import hashlib
import json
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ai import repository as ai_repository
from app.ai.gateway import Gateway, Progress
from app.ai.generation import generation_prompts
from app.ai.phase6 import phase6_prompts
from app.ai.prompts import job_prompt, messages
from app.ai.retrieval import match
from app.ai.service import EXTRACTION_VERSION, analyze_job
from app.jobs import repository, schemas
from app.jobs.schemas import AnalysisResult, Job, JobAnalysis, JobInput, PromptInfo
from app.settings import service as settings


def list_jobs(db: Session, owner: UUID) -> list[Job]:
    return repository.list_jobs(db, owner)


def create(db: Session, owner: UUID, data: JobInput) -> Job:
    return repository.create(db, owner, data)


def prompts(db: Session, owner: UUID) -> list[PromptInfo]:
    prompt = job_prompt()
    result = [prompt, *generation_prompts(), *phase6_prompts()]
    for entry in result:
        ai_repository.seed_prompt(db, owner, entry)
    return result


def get(db: Session, owner: UUID, identifier: UUID) -> Job:
    job = repository.find(db, owner, identifier)
    if job is None:
        raise HTTPException(404, "Job description not found")
    return job


async def analyze(
    db: Session,
    owner: UUID,
    identifier: UUID,
    gateway: Gateway,
    use_embeddings: bool,
    progress: Progress | None = None,
) -> AnalysisResult:
    job = get(db, owner, identifier)
    endpoint, profile = settings.resolve(db, owner, "job_analysis")
    prompt = job_prompt()
    ai_repository.seed_prompt(db, owner, prompt)
    system, user = messages(job.raw_text, prompt, profile.structured_mode != "json_schema")
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "text": job.raw_text,
                "endpoint": endpoint.model_dump(mode="json"),
                "profile": profile.model_dump(mode="json"),
                "prompt": prompt.digest,
                "rendered_prompt": [system, user],
                "schema": JobAnalysis.model_json_schema(),
                "extraction_version": EXTRACTION_VERSION,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    row = repository.cached(db, owner, identifier, fingerprint)
    cached = row is not None
    if progress:
        await progress("Using saved job analysis" if cached else "Analyzing job requirements")
    if row is None:
        analysis = await analyze_job(gateway, endpoint, profile, job.raw_text, prompt, progress)
        row = repository.save_analysis(
            db,
            owner,
            job.id,
            fingerprint,
            profile.model,
            f"{prompt.key}:v{prompt.version}:{prompt.digest}",
            analysis,
        )
    analysis = row.analysis
    # The cache covers posting interpretation only. Matching must run again so
    # career edits/retirements take effect even when the posting is unchanged.
    if progress:
        await progress("Matching current career evidence")
    matched = await match(db, owner, job, analysis, gateway, use_embeddings, progress)
    repository.save_match(db, owner, row.id, matched, cached)
    return AnalysisResult(
        id=row.id,
        job_id=job.id,
        analysis=analysis,
        match=matched,
        model=row.model,
        prompt_version=row.prompt_version,
        cached=cached,
    )


def analyses(db: Session, owner: UUID) -> list[schemas.AnalysisChoice]:
    return repository.analyses(db, owner)


def analysis(db: Session, owner: UUID, identifier: UUID) -> tuple[UUID, JobAnalysis]:
    result = repository.get_analysis(db, owner, identifier)
    if result is None:
        raise HTTPException(404, "Saved analysis not found")
    return result
