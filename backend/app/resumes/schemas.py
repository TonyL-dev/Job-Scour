from datetime import date, datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import Field, HttpUrl, model_validator

from app.career.schemas import Contract, Text

SourceType = Literal[
    "experience",
    "achievement",
    "project",
    "education",
    "course",
    "skill",
    "certification",
    "volunteer_experience",
    "award",
    "publication",
    "custom_entry",
]
SectionType = Literal[
    "summary",
    "experience",
    "projects",
    "skills",
    "education",
    "certifications",
    "volunteer",
    "awards",
    "publications",
    "custom",
]


class SourceRef(Contract):
    entity_type: SourceType
    entity_id: UUID


class DisplayFacts(Contract):
    employer: str | None = None
    title: str | None = None
    institution: str | None = None
    degree: str | None = None
    location: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    current: bool = False


class Item(Contract):
    key: UUID
    text: Text
    origin: Literal["user", "ai"]
    source_refs: list[SourceRef]
    locked: bool = False
    facts: DisplayFacts | None = None

    @model_validator(mode="after")
    def provenance(self) -> Self:
        refs = [(ref.entity_type, ref.entity_id) for ref in self.source_refs]
        if len(refs) != len(set(refs)):
            raise ValueError("Duplicate source references")
        if self.origin == "ai" and not refs:
            raise ValueError("AI text requires source references")
        return self


class Section(Contract):
    key: UUID
    type: SectionType
    title: Text
    visible: bool = True
    locked: bool = False
    items: list[Item] = Field(max_length=500)


class Link(Contract):
    label: Text
    url: HttpUrl


class Header(Contract):
    name: Text
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    links: list[Link] = Field(default_factory=list, max_length=30)


class StyleOverrides(Contract):
    font_family: Literal["sans", "serif"] | None = None
    font_size_pt: float | None = Field(default=None, ge=9, le=14)
    line_height: float | None = Field(default=None, ge=1, le=2)
    margin_mm: float | None = Field(default=None, ge=10, le=30)
    accent_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    section_spacing_mm: float | None = Field(default=None, ge=0, le=15)


class Metadata(Contract):
    template_id: UUID
    target_page_limit: int = Field(default=2, ge=1, le=10)
    job_description_id: UUID | None = None
    style_overrides: StyleOverrides = Field(default_factory=StyleOverrides)
    custom_template: "TemplateSnapshot | None" = None


class TemplateSnapshot(Contract):
    owner_id: UUID
    name: str
    base: Literal["classic", "modern"]
    html: str
    css: str
    styles: StyleOverrides
    assets: dict[str, str] = Field(default_factory=dict)
    digest: str
    findings: list[str] = Field(default_factory=list)


class ResumeDocument(Contract):
    schema_version: Literal[1]
    header: Header
    sections: list[Section] = Field(max_length=100)
    metadata: Metadata

    @model_validator(mode="after")
    def unique_keys(self) -> Self:
        keys = [section.key for section in self.sections]
        keys += [item.key for section in self.sections for item in section.items]
        if len(keys) != len(set(keys)):
            raise ValueError("Section and item keys must be unique")
        return self


class TemplateInfo(Contract):
    id: UUID
    name: str
    builtin_key: Literal["classic", "modern"]
    ats_safe: bool = True
    default_styles: StyleOverrides


class SaveResume(Contract):
    title: Text
    gold_standard: bool = False
    content: ResumeDocument
    expected_version: int = Field(default=0, ge=0)
    autosave: bool = False


class MasterResume(Contract):
    id: UUID
    title: str
    gold_standard: bool
    version_number: int
    updated_at: datetime
    content: ResumeDocument
    kind: Literal["master", "tailored"] = "master"
    parent_document_id: UUID | None = None


class Preview(Contract):
    html: str
    pdf_base64: str
    page_count: int
    html_hash: str
    warnings: list[str]


class ResumeVersion(Contract):
    id: UUID
    document_id: UUID
    version_number: int
    created_at: datetime
    content: ResumeDocument
    content_hash: str
    change_kind: Literal["user", "autosave", "restore", "duplicate", "ai"] = "user"
    restored_from_version_id: UUID | None = None


class VersionAction(Contract):
    expected_version: int = Field(ge=1)
    title: Text | None = None
