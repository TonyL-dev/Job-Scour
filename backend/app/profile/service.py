import re
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ai.gateway import Gateway
from app.ai.operations import operation
from app.ai.phase6 import profile_questions, provenance
from app.career import service as career
from app.career.schemas import CareerRecord
from app.core.workspace import validate_session
from app.profile import repository
from app.profile.schemas import Answers, Confirm, ProfileReview, Start
from app.settings import service as settings


def list_reviews(db: Session, owner: UUID) -> list[ProfileReview]:
    return repository.list_reviews(db, owner)


def current(db: Session, owner: UUID, review: ProfileReview) -> CareerRecord:
    record = career.get(db, owner, review.source.data.type, review.source.id)
    if record.data != review.source.data or record.updated_at != review.source.updated_at:
        raise HTTPException(409, "Career evidence changed; start a new profile review")
    return record


async def start(db: Session, owner: UUID, data: Start, gateway: Gateway) -> ProfileReview:
    source = career.get(db, owner, data.kind, data.record_id)
    endpoint, profile = settings.resolve(db, owner, "profile_questions")
    async with operation(owner, data.record_id):
        questions = await profile_questions(gateway, endpoint, profile, source)
        if any(
            len(q) > 1000 or not q.endswith("?") or re.search(r"\d", q) for q in questions.questions
        ):
            raise HTTPException(
                502, "Questions suggested numbers or exceeded question bounds; retry"
            )
    validate_session(db)
    if career.get(db, owner, data.kind, data.record_id) != source:
        raise HTTPException(409, "Career evidence changed during questions; retry")
    return repository.create(
        db,
        owner,
        {
            "source": source.model_dump(mode="json"),
            "questions": questions.questions,
            "answers": [],
            "proposed": None,
            "provenance": provenance("profile_questions", endpoint, profile),
        },
    )


def answer(db: Session, owner: UUID, identifier: UUID, data: Answers) -> ProfileReview:
    review = repository.get(db, owner, identifier)
    current(db, owner, review)
    if len(data.answers) != len(review.questions) or any(len(a) > 2000 for a in data.answers):
        raise HTTPException(422, "Supply one answer per question, at most 2000 characters each")
    factual = [
        a.strip()
        for a in data.answers
        if a.strip().casefold() not in {"", "skip", "unknown", "i don't know"}
    ]
    proposed = review.source.data.model_copy(deep=True)
    # The model supplies questions only. User answers form the proposed evidence;
    # saving this review does not update career facts until explicit confirmation.
    field = "text" if proposed.type == "achievement" else "description"
    setattr(
        proposed, field, getattr(proposed, field) + ("\n" + "\n".join(factual) if factual else "")
    )
    result = repository.change(
        db,
        owner,
        identifier,
        data.expected_revision,
        {
            "source": review.source.model_dump(mode="json"),
            "questions": review.questions,
            "answers": data.answers,
            "proposed": proposed.model_dump(mode="json"),
            "provenance": review.provenance,
        },
    )
    db.commit()
    return result


def confirm(db: Session, owner: UUID, identifier: UUID, data: Confirm) -> ProfileReview:
    review = repository.get(db, owner, identifier)
    if review.status == "confirmed":
        return review
    record = current(db, owner, review)
    if data.data.type != record.data.type or not review.answers:
        raise HTTPException(422, "Review your answers before confirming the same record type")
    try:
        result = repository.change(
            db,
            owner,
            identifier,
            data.expected_revision,
            {
                "source": review.source.model_dump(mode="json"),
                "questions": review.questions,
                "answers": review.answers,
                "proposed": data.data.model_dump(mode="json"),
                "provenance": review.provenance,
            },
            "confirmed",
        )
        career.save_if_current(db, owner, record, data.data)
        db.commit()
        return result
    except BaseException:
        db.rollback()
        raise


def discard(db: Session, owner: UUID, identifier: UUID, revision: int) -> ProfileReview:
    review = repository.get(db, owner, identifier)
    result = repository.change(
        db,
        owner,
        identifier,
        revision,
        {
            "source": review.source.model_dump(mode="json"),
            "questions": review.questions,
            "answers": [],
            "proposed": None,
            "provenance": review.provenance,
        },
        "discarded",
    )
    db.commit()
    return result
