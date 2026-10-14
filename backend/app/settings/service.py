from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ai.gateway import Gateway
from app.settings import repository as repo
from app.settings.schemas import (
    Assignment,
    ConnectionResult,
    Endpoint,
    EndpointInput,
    Profile,
    ProfileInput,
    Task,
    WorkspaceSettings,
)


def read(db: Session, owner: UUID) -> WorkspaceSettings:
    return WorkspaceSettings(
        endpoints=repo.endpoints(db, owner),
        profiles=repo.profiles(db, owner),
        assignments=repo.assignments(db, owner),
    )


async def test_profile(
    db: Session, owner: UUID, identifier: UUID, gateway: Gateway
) -> ConnectionResult:
    selected = profile(db, owner, identifier)
    assignments = read(db, owner).assignments
    destination = endpoint(db, owner, selected.endpoint_id)
    if any(a.task == "embeddings" and a.profile_id == identifier for a in assignments) and not any(
        a.task != "embeddings" and a.profile_id == identifier for a in assignments
    ):
        await gateway.embed(destination, selected, "search_query: connectivity test")
        return ConnectionResult(ok=True)
    return await gateway.test(destination, selected)


def endpoint(db: Session, owner: UUID, identifier: UUID) -> Endpoint:
    row = repo.find_endpoint(db, owner, identifier)
    if row is None:
        raise HTTPException(404, "Endpoint not found")
    return repo.endpoint(row)


def save_endpoint(
    db: Session, owner: UUID, data: EndpointInput, identifier: UUID | None = None
) -> Endpoint:
    row = None
    if identifier:
        endpoint(db, owner, identifier)
        row = repo.find_endpoint(db, owner, identifier)
    return repo.save_endpoint(db, owner, data, row)


def save_profile(db: Session, owner: UUID, data: ProfileInput) -> Profile:
    destination = endpoint(db, owner, data.endpoint_id)
    if destination.provider == "codex" and data.structured_mode != "json_schema":
        raise HTTPException(422, "Codex profiles require JSON schema output")
    return repo.save_profile(db, owner, data)


def profile(db: Session, owner: UUID, identifier: UUID) -> Profile:
    row = repo.find_profile(db, owner, identifier)
    if row is None:
        raise HTTPException(404, "Model profile not found")
    return repo.profile(row)


def assign(db: Session, owner: UUID, data: Assignment) -> Assignment:
    selected = profile(db, owner, data.profile_id)
    if data.task == "embeddings" and endpoint(db, owner, selected.endpoint_id).provider == "codex":
        raise HTTPException(422, "Codex does not provide embeddings. Use keyword matching.")
    return repo.assign(db, owner, data)


def resolve(db: Session, owner: UUID, task: Task) -> tuple[Endpoint, Profile]:
    assignment = next((a for a in repo.assignments(db, owner) if a.task == task), None)
    if assignment is None:
        raise HTTPException(409, f"Assign a model to {task.replace('_', ' ')} in AI settings first")
    selected = profile(db, owner, assignment.profile_id)
    from app.prompt_management import repository as prompt_repository
    from app.prompt_management.service import base_digest, preference

    custom = prompt_repository.active(db, owner, task)
    if custom:
        if custom.base_digest != base_digest(task):
            raise HTTPException(
                409, "Active customization uses an older base prompt; fork and evaluate again"
            )
        selected = selected.model_copy(
            update={"custom_preference": preference(custom), "custom_digest": custom.digest}
        )
    return endpoint(db, owner, selected.endpoint_id), selected
