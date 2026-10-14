from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.models import Embedding, PromptVersion
from app.jobs.schemas import PromptInfo


def refresh_session(db: Session) -> None:
    db.expire_all()


def seed_prompt(db: Session, owner: UUID, data: PromptInfo) -> None:
    row = db.scalar(
        select(PromptVersion).where(
            PromptVersion.user_id == owner,
            PromptVersion.key == data.key,
            PromptVersion.version == data.version,
            PromptVersion.digest == data.digest,
        )
    )
    if row is None:
        db.add(PromptVersion(user_id=owner, **data.model_dump()))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()


def embedding(
    db: Session, owner: UUID, kind: str, identifier: UUID, model_key: str, digest: str
) -> list[float] | None:
    row = db.scalar(
        select(Embedding).where(
            Embedding.user_id == owner,
            Embedding.entity_type == kind,
            Embedding.entity_id == identifier,
            Embedding.model_key == model_key,
            Embedding.content_hash == digest,
        )
    )
    return row.vector if row else None


def save_embedding(
    db: Session,
    owner: UUID,
    kind: str,
    identifier: UUID,
    model_key: str,
    digest: str,
    vector: list[float],
) -> None:
    db.add(
        Embedding(
            user_id=owner,
            entity_type=kind,
            entity_id=identifier,
            model_key=model_key,
            content_hash=digest,
            vector=vector,
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
