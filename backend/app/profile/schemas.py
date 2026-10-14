from typing import Literal
from uuid import UUID

from pydantic import Field

from app.career.schemas import CareerInput, CareerRecord, Contract


class Start(Contract):
    kind: Literal["achievement", "project", "experience"]
    record_id: UUID


class Questions(Contract):
    questions: list[str] = Field(min_length=1, max_length=6)


class ProfileReview(Contract):
    id: UUID
    revision: int
    source: CareerRecord
    questions: list[str]
    answers: list[str]
    status: Literal["review", "confirmed", "discarded"]
    proposed: CareerInput | None = None
    provenance: dict[str, str] = Field(default_factory=dict)


class Answers(Contract):
    expected_revision: int = Field(ge=1)
    answers: list[str] = Field(max_length=6)


class Confirm(Contract):
    expected_revision: int = Field(ge=1)
    data: CareerInput
