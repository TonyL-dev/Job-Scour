from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.career.schemas import Contract
from app.resumes.schemas import SourceRef


class JobInput(Contract):
    company: str = Field(default="", max_length=200)
    title: str = Field(default="", max_length=200)
    location: str = Field(default="", max_length=200)
    url: str = Field(default="", max_length=2000, pattern=r"^$|^https?://")
    raw_text: str = Field(min_length=20, max_length=30000)


class Job(JobInput):
    id: UUID
    created_at: datetime


class Requirement(Contract):
    term: str = Field(min_length=1, max_length=240)
    evidence: str = Field(min_length=1, max_length=1000)


class Keyword(Requirement):
    weight: int = Field(ge=1, le=5, strict=True)


class JobAnalysis(Contract):
    required_skills: list[Requirement] = Field(max_length=50)
    preferred_skills: list[Requirement] = Field(max_length=50)
    technologies: list[Requirement] = Field(max_length=50)
    responsibilities: list[Requirement] = Field(max_length=50)
    company_values: list[Requirement] = Field(max_length=30)
    industry_terms: list[Requirement] = Field(max_length=30)
    keywords: list[Keyword] = Field(max_length=80)
    seniority: Requirement | None
    years_experience: Requirement | None


class MatchItem(Contract):
    source_ref: SourceRef
    label: str
    score: float
    keyword_score: float
    semantic_score: float | None
    matched_keywords: list[str]
    reasons: list[str]


class MatchAnalysis(Contract):
    items: list[MatchItem]
    missing_keywords: list[str]
    strengths: list[str]
    emphasis_areas: list[str]
    keyword_coverage: float
    retrieval_mode: Literal["keywords", "embeddings_and_keywords"]
    warnings: list[str]
    career_snapshot_hash: str


class AnalysisResult(Contract):
    id: UUID
    job_id: UUID
    analysis: JobAnalysis
    match: MatchAnalysis
    model: str
    prompt_version: str
    cached: bool


class AnalyzeInput(Contract):
    use_embeddings: bool = False


class PromptInfo(Contract):
    key: str
    version: str
    digest: str
    system_text: str
    user_template: str


class AnalysisChoice(Contract):
    id: UUID
    job_id: UUID
    company: str
    title: str
    created_at: datetime
