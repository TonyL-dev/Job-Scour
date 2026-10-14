from typing import Literal
from uuid import UUID

from pydantic import Field

from app.career.schemas import Contract
from app.settings.schemas import Task


class PromptFork(Contract):
    task: Task
    name: str = Field(min_length=1, max_length=120)
    tone: Literal["plain", "formal", "concise"] = "plain"
    focus: Literal["clarity", "impact", "technical"] = "clarity"
    notes: str = Field(default="", max_length=1000)
    parent_id: UUID | None = None


class CustomPrompt(PromptFork):
    id: UUID
    digest: str
    base_digest: str


class EvaluationReport(Contract):
    id: UUID
    prompt_id: UUID
    passed: bool
    configuration_digest: str
    results: list[dict[str, object]]


class Activation(Contract):
    task: Task
    prompt_id: UUID
    expected_prompt_id: UUID | None = None
    report_id: UUID


class Reset(Contract):
    task: Task
    expected_prompt_id: UUID
