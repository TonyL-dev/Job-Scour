from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.career.schemas import Contract
from app.resumes.schemas import Item, ResumeDocument

RunStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]


class GenerateInput(Contract):
    master_id: UUID
    job_id: UUID
    use_embeddings: bool = False
    section_keys: list[UUID] = Field(default_factory=list, max_length=100)
    item_keys: list[UUID] = Field(default_factory=list, max_length=500)
    instruction: str = Field(default="", max_length=1000)
    preset: Literal[
        "tailor", "rewrite_summary", "quantify", "concise", "senior", "technical", "fit"
    ] = "tailor"
    allow_layout_adjustments: bool = False
    parent_run_id: UUID | None = None


class Suggestion(Contract):
    id: UUID
    section_key: UUID
    item_key: UUID
    original: Item | None
    proposed: Item | None
    verification: Literal["supported", "partially_supported", "unsupported"]
    reason: str
    sources: dict[str, str] = Field(default_factory=dict)
    rejected_text: str | None = None
    order_keys: list[UUID] | None = None


class RunEvent(Contract):
    sequence: int
    stage: str
    elapsed_seconds: float


class GenerationRun(Contract):
    id: UUID
    created_at: datetime
    status: RunStatus
    request: GenerateInput
    base: ResumeDocument
    proposed: ResumeDocument | None
    suggestions: list[Suggestion]
    events: list[RunEvent]
    page_count: int | None
    warnings: list[str]
    error: str | None
    provenance: dict[str, str]
    saved_version_id: UUID | None = None
    saved_resume_id: UUID | None
    review_revision: int
    decisions: list["Decision"] = Field(default_factory=list)
    locks: dict[str, bool] = Field(default_factory=dict)


class Decision(Contract):
    suggestion_id: UUID
    action: Literal["accept", "reject", "edit"]
    text: str | None = Field(default=None, min_length=1, max_length=10000)

    @model_validator(mode="after")
    def edited_text(self) -> "Decision":
        if self.action == "edit" and not self.text:
            raise ValueError("Edited decisions require text")
        return self


class ReviewInput(Contract):
    decisions: list[Decision] = Field(default_factory=list, max_length=1000)
    expected_revision: int = Field(default=0, ge=0)
    locks: dict[str, bool] = Field(default_factory=dict, max_length=600)


class CommitReview(ReviewInput):
    title: str = Field(min_length=1, max_length=200)


class RankedChoice(Contract):
    source_id: UUID
    reason: str = Field(min_length=1, max_length=500)


class Selection(Contract):
    choices: list[RankedChoice] = Field(max_length=24)


class Rewrite(Contract):
    text: str = Field(min_length=1, max_length=1500)
    source_ids: list[UUID] = Field(min_length=1, max_length=10)


class Verification(Contract):
    status: Literal["supported", "partially_supported", "unsupported"]
    reason: str = Field(min_length=1, max_length=1000)
