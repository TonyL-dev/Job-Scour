from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.settings.models import LLMEndpoint, ModelProfile, TaskAssignment
from app.settings.schemas import Assignment, Endpoint, EndpointInput, Profile, ProfileInput


def endpoint(row: LLMEndpoint) -> Endpoint:
    return Endpoint.model_validate({key: getattr(row, key) for key in Endpoint.model_fields})


def profile(row: ModelProfile) -> Profile:
    return Profile.model_validate(
        {key: getattr(row, key) for key in ProfileInput.model_fields} | {"id": row.id}
    )


def endpoints(db: Session, owner: UUID) -> list[Endpoint]:
    return [
        endpoint(r) for r in db.scalars(select(LLMEndpoint).where(LLMEndpoint.user_id == owner))
    ]


def profiles(db: Session, owner: UUID) -> list[Profile]:
    return [
        profile(r) for r in db.scalars(select(ModelProfile).where(ModelProfile.user_id == owner))
    ]


def assignments(db: Session, owner: UUID) -> list[Assignment]:
    return [
        Assignment(task=r.task, profile_id=r.profile_id)
        for r in db.scalars(select(TaskAssignment).where(TaskAssignment.user_id == owner))
    ]


def find_endpoint(db: Session, owner: UUID, identifier: UUID) -> LLMEndpoint | None:
    return db.scalar(
        select(LLMEndpoint).where(LLMEndpoint.user_id == owner, LLMEndpoint.id == identifier)
    )


def find_profile(db: Session, owner: UUID, identifier: UUID) -> ModelProfile | None:
    return db.scalar(
        select(ModelProfile).where(ModelProfile.user_id == owner, ModelProfile.id == identifier)
    )


def save_endpoint(
    db: Session, owner: UUID, data: EndpointInput, row: LLMEndpoint | None
) -> Endpoint:
    row = row or LLMEndpoint(user_id=owner)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    db.add(row)
    db.commit()
    return endpoint(row)


def save_profile(db: Session, owner: UUID, data: ProfileInput) -> Profile:
    row = ModelProfile(user_id=owner, **data.model_dump())
    db.add(row)
    db.commit()
    return profile(row)


def assign(db: Session, owner: UUID, data: Assignment) -> Assignment:
    row = db.scalar(
        select(TaskAssignment).where(
            TaskAssignment.user_id == owner, TaskAssignment.task == data.task
        )
    )
    row = row or TaskAssignment(user_id=owner, task=data.task)
    row.profile_id = data.profile_id
    db.add(row)
    db.commit()
    return data
