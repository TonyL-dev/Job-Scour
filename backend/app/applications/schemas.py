from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.career.schemas import Contract

Stage = Literal["saved", "applied", "screen", "interview", "offer", "rejected", "withdrawn"]


class ApplicationInput(Contract):
    company: str = Field(min_length=1, max_length=200)
    position: str = Field(min_length=1, max_length=200)
    job_id: UUID | None = None
    version_id: UUID
    cover_letter_version_id: UUID | None = None
    date_applied: date | None = None
    stage: Stage = "saved"
    channel: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=10000)
    follow_up_date: date | None = None
    follow_up_done: bool = False


class ApplicationSave(ApplicationInput):
    expected_revision: int = Field(default=0, ge=0)


class Application(ApplicationInput):
    document_id: UUID
    version_number: int
    id: UUID
    revision: int
    created_at: datetime
    updated_at: datetime


class EventInput(Contract):
    stage: Stage
    date: date
    notes: str = Field(default="", max_length=5000)
    expected_revision: int = Field(ge=1)


class ApplicationEvent(Contract):
    id: UUID
    application_id: UUID
    stage: Stage
    date: date
    notes: str
