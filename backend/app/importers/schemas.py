from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from app.career.schemas import CareerType, Contract


class Upload(Contract):
    filename: str = Field(min_length=1, max_length=180)
    mime: Literal[
        "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
    content_base64: str = Field(max_length=2800000)
    retain_original: bool = False


class Fragment(Contract):
    locator: str
    text: str = Field(max_length=200000)


class Candidate(Contract):
    key: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    data: dict[str, Any]
    locator: str
    excerpt: str = Field(max_length=20000)
    decision: Literal["pending", "accepted", "rejected"] = "pending"
    user_supplied: bool = False
    duplicate_ids: list[UUID] = Field(default_factory=list)


class Review(Contract):
    expected_revision: int = Field(ge=1)
    candidates: list[Candidate] = Field(max_length=100)


class ImportRun(Contract):
    id: UUID
    filename: str
    revision: int
    status: Literal["parsing", "failed", "review", "committed", "discarded"]
    fragments: list[Fragment]
    candidates: list[Candidate]
    saved_ids: list[UUID]
    original_available: bool
    provenance: dict[str, str] = Field(default_factory=dict)
    error: str | None = None


class ExtractedData(Contract):
    # Closed staging schema is compatible with Codex strict output. Missing values stay null;
    # full career validation occurs only after user review and parent resolution.
    type: CareerType
    company: str | None = None
    job_title: str | None = None
    name: str | None = None
    title: str | None = None
    organization: str | None = None
    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    description: str | None = None
    text: str | None = None
    role: str | None = None
    location: str | None = None
    industry: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    current: bool | None = None
    experience_id: str | None = None
    project_id: str | None = None
    education_id: str | None = None
    skill_id: str | None = None
    achievement_id: str | None = None
    metric_value: str | None = None
    metric_unit: str | None = None
    metric_description: str | None = None
    category: str | None = None
    proficiency: str | None = None
    years_of_use: str | None = None
    aliases: list[str] | None = None
    challenges_solved: str | None = None
    results: str | None = None
    issuer: str | None = None
    issue_date: str | None = None
    expiry_date: str | None = None
    credential_id: str | None = None
    url: str | None = None
    gpa: str | None = None
    honors: str | None = None
    date: str | None = None
    venue: str | None = None
    co_authors: list[str] | None = None


class ExtractedCandidate(Contract):
    key: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    data: ExtractedData
    locator: str
    excerpt: str = Field(min_length=1, max_length=20000)


class Extraction(Contract):
    candidates: list[ExtractedCandidate] = Field(max_length=100)
