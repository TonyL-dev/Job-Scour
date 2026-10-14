from datetime import UTC
from uuid import UUID

from sqlalchemy import Engine, inspect, select, update
from sqlalchemy.orm import Session

from app.resumes.generation_models import GenerationRecord, SuggestionRecord
from app.resumes.generation_schemas import (
    Decision,
    GenerateInput,
    GenerationRun,
    RunEvent,
    Suggestion,
)
from app.resumes.schemas import ResumeDocument


def find(db: Session, owner: UUID, identifier: UUID) -> GenerationRecord | None:
    return db.scalar(
        select(GenerationRecord)
        .where(GenerationRecord.user_id == owner, GenerationRecord.id == identifier)
        .execution_options(populate_existing=True)
    )


def read(db: Session, row: GenerationRecord) -> GenerationRun:
    suggestions = db.scalars(
        select(SuggestionRecord)
        .where(
            SuggestionRecord.user_id == row.user_id,
            SuggestionRecord.run_id == row.id,
            SuggestionRecord.id.in_([UUID(i) for i in row.suggestion_ids]),
        )
        .order_by(SuggestionRecord.created_at, SuggestionRecord.id)
    )
    return GenerationRun(
        id=row.id,
        created_at=row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=UTC),
        status=row.status,
        request=GenerateInput.model_validate(row.request_snapshot),
        base=ResumeDocument.model_validate(row.base_snapshot),
        proposed=ResumeDocument.model_validate(row.proposed_snapshot)
        if row.proposed_snapshot
        else None,
        suggestions=[Suggestion.model_validate(s.snapshot) for s in suggestions],
        events=[RunEvent.model_validate(e) for e in row.events],
        page_count=row.page_count,
        warnings=row.warnings,
        error=row.error,
        provenance=row.provenance,
        saved_resume_id=row.saved_resume_id,
        saved_version_id=row.saved_version_id,
        review_revision=row.review_revision,
        decisions=[Decision.model_validate(d) for d in row.decisions],
        locks=row.review_locks,
    )


def list_runs(db: Session, owner: UUID) -> list[GenerationRun]:
    return [
        read(db, row)
        for row in db.scalars(
            select(GenerationRecord)
            .where(GenerationRecord.user_id == owner)
            .order_by(GenerationRecord.created_at.desc())
            .limit(100)
        )
    ]


def create(db: Session, owner: UUID, data: GenerateInput, base: ResumeDocument) -> GenerationRun:
    row = GenerationRecord(
        user_id=owner,
        master_id=data.master_id,
        job_id=data.job_id,
        status="queued",
        request_snapshot=data.model_dump(mode="json"),
        base_snapshot=base.model_dump(mode="json"),
    )
    db.add(row)
    db.commit()
    return read(db, row)


def progress(db: Session, owner: UUID, identifier: UUID, event: RunEvent) -> None:
    row = find(db, owner, identifier)
    assert row is not None
    row.events = [*row.events, event.model_dump(mode="json")]
    row.status = "running"
    db.commit()


def checkpoint(
    db: Session,
    owner: UUID,
    identifier: UUID,
    content: ResumeDocument,
    suggestions: list[Suggestion],
    provenance: dict[str, str],
) -> None:
    row = find(db, owner, identifier)
    assert row is not None
    row.proposed_snapshot = content.model_dump(mode="json")
    row.provenance = dict(provenance)
    row.suggestion_ids = [str(s.id) for s in suggestions]
    existing = set(
        db.scalars(
            select(SuggestionRecord.id).where(
                SuggestionRecord.user_id == owner, SuggestionRecord.run_id == identifier
            )
        )
    )
    for suggestion in suggestions:
        if suggestion.id not in existing:
            db.add(
                SuggestionRecord(
                    id=suggestion.id,
                    user_id=owner,
                    run_id=identifier,
                    snapshot=suggestion.model_dump(mode="json"),
                )
            )
    db.commit()


def finish(
    db: Session,
    owner: UUID,
    identifier: UUID,
    status: str,
    *,
    pages: int | None = None,
    warnings: list[str] | None = None,
    error: str | None = None,
) -> None:
    row = find(db, owner, identifier)
    assert row is not None
    row.status = status
    row.page_count = pages
    row.warnings = warnings or []
    row.error = error
    db.commit()


def recover(engine: Engine) -> None:
    if not inspect(engine).has_table("generation_runs"):
        return
    with Session(engine) as db:
        db.execute(
            update(GenerationRecord)
            .where(GenerationRecord.status.in_(["queued", "running"]))
            .values(
                status="failed",
                error=(
                    "Backend stopped during generation. Saved partial suggestions remain "
                    "reviewable; start a new run to retry."
                ),
            )
        )
        db.commit()


def record_review(
    db: Session,
    owner: UUID,
    identifier: UUID,
    revision: int,
    decisions: list[dict[str, object]],
    locks: dict[str, bool],
) -> bool:
    result = db.execute(
        update(GenerationRecord)
        .where(
            GenerationRecord.user_id == owner,
            GenerationRecord.id == identifier,
            GenerationRecord.review_revision == revision,
        )
        .values(decisions=decisions, review_locks=locks, review_revision=revision + 1)
    )
    return bool(result.rowcount == 1)  # type: ignore[attr-defined]


def link_saved_resume(
    db: Session, owner: UUID, identifier: UUID, saved_id: UUID, version_id: UUID
) -> None:
    row = find(db, owner, identifier)
    assert row is not None
    row.saved_resume_id = saved_id
    row.saved_version_id = version_id
    db.commit()
