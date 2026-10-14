from typing import Literal
from uuid import UUID

from pydantic import Field

from app.career.schemas import Contract
from app.resumes.schemas import Header, Item, SourceRef


class LetterContent(Contract):
    author: Header
    recipient: str = Field(default="", max_length=500)
    salutation: str = Field(default="Dear hiring team,", max_length=200)
    closing: str = Field(default="Sincerely,", max_length=200)
    paragraphs: list[Item] = Field(default_factory=list, max_length=6)


class LetterStart(Contract):
    title: str = Field(min_length=1, max_length=200)
    job_id: UUID
    analysis_id: UUID
    resume_version_id: UUID | None = None
    sources: list[SourceRef] = Field(min_length=1, max_length=10)
    content: LetterContent
    max_words: int = Field(default=400, ge=100, le=600)


class Paragraphs(Contract):
    paragraphs: list[Item] = Field(min_length=1, max_length=6)


class LetterRun(Contract):
    id: UUID
    revision: int
    status: Literal["queued", "running", "review", "failed", "cancelled", "committed"]
    request: LetterStart
    proposed: LetterContent
    support: dict[str, str]
    reasons: dict[str, str]
    evidence: dict[str, str]
    provenance: dict[str, str]
    error: str | None = None
    saved_version_id: UUID | None = None


class LetterReview(Contract):
    expected_revision: int = Field(ge=1)
    content: LetterContent


class LetterVersion(Contract):
    id: UUID
    document_id: UUID
    version_number: int
    title: str
    job_id: UUID
    content: LetterContent
    provenance: dict[str, str]


class LetterSave(LetterReview):
    title: str = Field(min_length=1, max_length=200)


class LetterEdit(Contract):
    expected_version: int = Field(ge=1)
    content: LetterContent
