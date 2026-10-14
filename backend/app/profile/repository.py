from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.profile.models import ProfileRun
from app.profile.schemas import ProfileReview


def dto(row: ProfileRun) -> ProfileReview:
    return ProfileReview(id=row.id, revision=row.revision, status=row.status, **row.payload)


def get(db: Session, owner: UUID, identifier: UUID) -> ProfileReview:
    row = db.scalar(
        select(ProfileRun).where(ProfileRun.user_id == owner, ProfileRun.id == identifier)
    )
    if row is None:
        raise HTTPException(404, "Profile review not found")
    return dto(row)


def list_reviews(db: Session, owner: UUID) -> list[ProfileReview]:
    return [
        dto(row)
        for row in db.scalars(
            select(ProfileRun)
            .where(ProfileRun.user_id == owner)
            .order_by(ProfileRun.created_at.desc())
            .limit(100)
        )
    ]


def create(db: Session, owner: UUID, payload: dict[str, object]) -> ProfileReview:
    row = ProfileRun(user_id=owner, payload=payload)
    db.add(row)
    db.commit()
    return dto(row)


def change(
    db: Session,
    owner: UUID,
    identifier: UUID,
    revision: int,
    payload: dict[str, object],
    status: str = "review",
) -> ProfileReview:
    result = db.execute(
        update(ProfileRun)
        .where(
            ProfileRun.user_id == owner,
            ProfileRun.id == identifier,
            ProfileRun.revision == revision,
            ProfileRun.status == "review",
        )
        .values(payload=payload, status=status, revision=revision + 1)
    )
    if result.rowcount != 1:  # type: ignore[attr-defined]
        raise HTTPException(409, "Profile review changed; reload")
    return get(db, owner, identifier)
