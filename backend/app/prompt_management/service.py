import hashlib
import json
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ai.gateway import Gateway
from app.ai.generation import generation_prompts
from app.ai.operations import operation
from app.ai.phase6 import phase6_prompts
from app.ai.prompt_evaluation import evaluate_case
from app.ai.prompts import job_prompt
from app.core.workspace import validate_session
from app.prompt_management import repository
from app.prompt_management.schemas import (
    Activation,
    CustomPrompt,
    EvaluationReport,
    PromptFork,
    Reset,
)
from app.settings import service as settings
from app.settings.schemas import Endpoint, Profile


def base_digest(task: str) -> str:
    for prompt in [job_prompt(), *generation_prompts(), *phase6_prompts()]:
        if prompt.key == task:
            return prompt.digest
    raise HTTPException(422, "This task has no supported chat prompt")


def preference(custom: CustomPrompt) -> str:
    return (
        f"Tone: {custom.tone}. Focus: {custom.focus}. Preserve factual evidence and output schema."
    )


def configuration_digest(
    endpoint: Endpoint, profile: Profile, verifier: tuple[Endpoint, Profile]
) -> str:
    return hashlib.sha256(
        json.dumps(
            [
                endpoint.model_dump(mode="json"),
                profile.model_dump(mode="json", exclude={"custom_preference", "custom_digest"}),
                verifier[0].model_dump(mode="json"),
                verifier[1].model_dump(mode="json"),
            ],
            sort_keys=True,
        ).encode()
    ).hexdigest()


def list_prompts(db: Session, owner: UUID) -> list[CustomPrompt]:
    return repository.list_prompts(db, owner)


def active_ids(db: Session, owner: UUID) -> dict[str, UUID]:
    return repository.active_ids(db, owner)


def fork(db: Session, owner: UUID, data: PromptFork) -> CustomPrompt:
    digest = base_digest(data.task)
    if data.parent_id:
        parent = repository.get(db, owner, data.parent_id)
        if parent.task != data.task:
            raise HTTPException(422, "Fork parent must use the same task")
    payload = data.model_dump(mode="json")
    custom_digest = hashlib.sha256(
        json.dumps([digest, payload], sort_keys=True).encode()
    ).hexdigest()
    return repository.create(db, owner, data.task, custom_digest, digest, payload)


async def evaluate(
    db: Session, owner: UUID, identifier: UUID, gateway: Gateway
) -> EvaluationReport:
    custom = repository.get(db, owner, identifier)
    if custom.base_digest != base_digest(custom.task):
        raise HTTPException(409, "Base prompt changed; fork a new version")
    endpoint, baseline = settings.resolve(db, owner, custom.task)
    verifier = settings.resolve(db, owner, "verification")
    candidate = baseline.model_copy(
        update={"custom_preference": preference(custom), "custom_digest": custom.digest}
    )
    results: list[dict[str, object]] = []
    async with operation(owner, identifier):
        for metric, injection in ((40, False), (25, False), (40, True)):
            pair: dict[str, object] = {
                "fixture": f"synthetic-metric-{metric}" + ("-injection" if injection else "")
            }
            for name, profile in (("baseline", baseline), ("candidate", candidate)):
                try:
                    pair[name] = await evaluate_case(
                        gateway, custom.task, endpoint, profile, verifier, metric, injection
                    )
                except (HTTPException, ValueError) as error:
                    pair[name] = {
                        "passed": False,
                        "error": "Model/schema/evidence evaluation failed",
                        "error_type": type(error).__name__,
                    }
            pair["passed"] = (
                isinstance(pair["candidate"], dict) and pair["candidate"].get("passed") is True
            )
            results.append(pair)
    validate_session(db)
    return repository.save_report(
        db, owner, identifier, configuration_digest(endpoint, baseline, verifier), results
    )


def activate(db: Session, owner: UUID, data: Activation) -> dict[str, UUID]:
    custom = repository.get(db, owner, data.prompt_id)
    report = repository.report(db, owner, data.report_id)
    endpoint, profile = settings.resolve(db, owner, data.task)
    verifier = settings.resolve(db, owner, "verification")
    if custom.task != data.task or custom.base_digest != base_digest(data.task):
        raise HTTPException(422, "Prompt task/base mismatch")
    # A passing report is valid only for this candidate and current writer/verifier
    # configuration; changing models/settings requires a new evaluation.
    if (
        report.prompt_id != custom.id
        or not report.passed
        or report.configuration_digest != configuration_digest(endpoint, profile, verifier)
    ):
        raise HTTPException(
            409,
            "Evaluate this prompt successfully with the current configuration before activating",
        )
    repository.activate(db, owner, data.task, custom.id, data.expected_prompt_id)
    return repository.active_ids(db, owner)


def get_report(db: Session, owner: UUID, identifier: UUID) -> EvaluationReport:
    return repository.report(db, owner, identifier)


def reset(db: Session, owner: UUID, data: Reset) -> dict[str, UUID]:
    repository.reset(db, owner, data.task, data.expected_prompt_id)
    return repository.active_ids(db, owner)


def reports(db: Session, owner: UUID, identifier: UUID) -> list[EvaluationReport]:
    return repository.reports(db, owner, identifier)
