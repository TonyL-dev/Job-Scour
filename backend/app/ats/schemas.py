from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.career.schemas import Contract
from app.resumes.schemas import SourceRef


class ReportInput(Contract):
    version_id: UUID
    analysis_id: UUID | None = None


class Finding(Contract):
    code: str
    severity: Literal["warning", "info"]
    message: str
    section_key: UUID | None = None
    item_key: UUID | None = None
    source_refs: list[SourceRef] = Field(default_factory=list)


class Report(Contract):
    id: UUID
    version_id: UUID
    analysis_id: UUID | None
    created_at: datetime
    engine_version: str
    overall_score: float
    sub_scores: dict[str, float]
    matched_keywords: list[str]
    missing_keywords: list[str]
    findings: list[Finding]
    page_count: int
    guidance: str = "Deterministic guidance, not a real ATS vendor verdict."
