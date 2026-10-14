from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.prompt_management.models import ActivePrompt, PromptCustomization, PromptEvaluation
from app.prompt_management.schemas import CustomPrompt, EvaluationReport


def dto(row: PromptCustomization) -> CustomPrompt:
    return CustomPrompt(id=row.id, digest=row.digest, base_digest=row.base_digest, **row.payload)


def get(db: Session, owner: UUID, identifier: UUID) -> CustomPrompt:
    row = db.scalar(
        select(PromptCustomization).where(
            PromptCustomization.user_id == owner, PromptCustomization.id == identifier
        )
    )
    if row is None:
        raise HTTPException(404, "Prompt version not found")
    return dto(row)


def list_prompts(db: Session, owner: UUID) -> list[CustomPrompt]:
    return [
        dto(row)
        for row in db.scalars(
            select(PromptCustomization)
            .where(PromptCustomization.user_id == owner)
            .order_by(PromptCustomization.created_at.desc())
        )
    ]


def create(
    db: Session, owner: UUID, task: str, digest: str, base_digest: str, payload: dict[str, object]
) -> CustomPrompt:
    row = PromptCustomization(
        user_id=owner, task=task, digest=digest, base_digest=base_digest, payload=payload
    )
    db.add(row)
    db.commit()
    return dto(row)


def report(db: Session, owner: UUID, identifier: UUID) -> EvaluationReport:
    row = db.scalar(
        select(PromptEvaluation).where(
            PromptEvaluation.user_id == owner, PromptEvaluation.id == identifier
        )
    )
    if row is None:
        raise HTTPException(404, "Evaluation report not found")
    return EvaluationReport(
        id=row.id,
        prompt_id=row.prompt_id,
        passed=row.passed,
        configuration_digest=row.configuration_digest,
        results=row.results,
    )


def save_report(
    db: Session,
    owner: UUID,
    prompt_id: UUID,
    configuration_digest: str,
    results: list[dict[str, object]],
) -> EvaluationReport:
    row = PromptEvaluation(
        user_id=owner,
        prompt_id=prompt_id,
        configuration_digest=configuration_digest,
        passed=all(r.get("passed") is True for r in results),
        results=results,
    )
    db.add(row)
    db.commit()
    return report(db, owner, row.id)


def active_ids(db: Session, owner: UUID) -> dict[str, UUID]:
    return {
        row.task: row.prompt_id
        for row in db.scalars(select(ActivePrompt).where(ActivePrompt.user_id == owner))
    }


def active(db: Session, owner: UUID, task: str) -> CustomPrompt | None:
    identifier = active_ids(db, owner).get(task)
    return get(db, owner, identifier) if identifier else None


def activate(db: Session, owner: UUID, task: str, prompt_id: UUID, expected: UUID | None) -> None:
    row = db.scalar(
        select(ActivePrompt).where(ActivePrompt.user_id == owner, ActivePrompt.task == task)
    )
    if (row.prompt_id if row else None) != expected:
        raise HTTPException(409, "Active prompt changed; reload before activating")
    try:
        if row:
            result = db.execute(
                update(ActivePrompt)
                .where(
                    ActivePrompt.user_id == owner,
                    ActivePrompt.task == task,
                    ActivePrompt.prompt_id == expected,
                )
                .values(prompt_id=prompt_id)
            )
            if result.rowcount != 1:  # type: ignore[attr-defined]
                raise HTTPException(409, "Active prompt changed; reload")
        else:
            db.add(ActivePrompt(user_id=owner, task=task, prompt_id=prompt_id))
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, "Active prompt changed; reload") from error


def reset(db: Session, owner: UUID, task: str, expected: UUID) -> None:
    result = db.execute(
        delete(ActivePrompt).where(
            ActivePrompt.user_id == owner,
            ActivePrompt.task == task,
            ActivePrompt.prompt_id == expected,
        )
    )
    if result.rowcount != 1:  # type: ignore[attr-defined]
        raise HTTPException(409, "Active prompt changed; reload")
    db.commit()


def reports(db: Session, owner: UUID, identifier: UUID) -> list[EvaluationReport]:
    get(db, owner, identifier)
    return [
        report(db, owner, row.id)
        for row in db.scalars(
            select(PromptEvaluation)
            .where(PromptEvaluation.user_id == owner, PromptEvaluation.prompt_id == identifier)
            .order_by(PromptEvaluation.created_at.desc())
        )
    ]
