from datetime import date as DateValue
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


Text = Annotated[str, Field(min_length=1, max_length=20000)]


class Dated(Contract):
    start_date: DateValue | None = None
    end_date: DateValue | None = None

    @model_validator(mode="after")
    def dates(self) -> Self:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date must not precede start date")
        if getattr(self, "current", False) and self.end_date:
            raise ValueError("Current entries cannot have an end date")
        return self


class Experience(Dated):
    type: Literal["experience"] = "experience"
    company: Text
    job_title: Text
    location: str | None = None
    employment_type: Literal[
        "full_time", "part_time", "contract", "internship", "freelance", "other"
    ] = "full_time"
    start_date: DateValue
    current: bool = False
    description: str = ""
    industry: str | None = None
    ordering_hint: int = 0


class Project(Dated):
    type: Literal["project"] = "project"
    experience_id: UUID | None = None
    name: Text
    description: str = ""
    role: str | None = None
    url: HttpUrl | None = None
    challenges_solved: str = ""
    results: str = ""


class Achievement(Contract):
    type: Literal["achievement"] = "achievement"
    experience_id: UUID | None = None
    project_id: UUID | None = None
    text: Text
    category: Literal["responsibility", "achievement", "impact"] = "achievement"
    metric_value: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    metric_unit: str | None = None
    metric_description: str | None = None
    verified_by_user: bool = False
    importance: int = Field(default=3, ge=1, le=5)

    @model_validator(mode="after")
    def parent(self) -> Self:
        if sum(value is not None for value in [self.experience_id, self.project_id]) != 1:
            raise ValueError("Choose exactly one experience or project")
        return self


class Education(Dated):
    type: Literal["education"] = "education"
    institution: Text
    degree: Text
    field: str | None = None
    gpa: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=4)
    honors: str | None = None


class Course(Contract):
    type: Literal["course"] = "course"
    education_id: UUID
    name: Text
    description: str = ""


class Skill(Contract):
    type: Literal["skill"] = "skill"
    name: Text
    category: Literal["language", "framework", "tool", "soft_skill", "domain"] = "tool"
    proficiency: Literal["beginner", "intermediate", "advanced", "expert"] | None = None
    years_of_use: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=4)
    last_used_date: DateValue | None = None
    aliases: list[Text] = Field(default_factory=list, max_length=100)


class SkillEvidence(Contract):
    type: Literal["skill_evidence"] = "skill_evidence"
    skill_id: UUID
    experience_id: UUID | None = None
    project_id: UUID | None = None
    achievement_id: UUID | None = None

    @model_validator(mode="after")
    def target(self) -> Self:
        if (
            sum(x is not None for x in [self.experience_id, self.project_id, self.achievement_id])
            != 1
        ):
            raise ValueError("Choose exactly one evidence target")
        return self


class Certification(Contract):
    type: Literal["certification"] = "certification"
    name: Text
    issuer: Text
    issue_date: DateValue | None = None
    expiry_date: DateValue | None = None
    credential_id: str | None = None
    url: HttpUrl | None = None

    @model_validator(mode="after")
    def dates(self) -> Self:
        if self.issue_date and self.expiry_date and self.expiry_date < self.issue_date:
            raise ValueError("Expiry date must not precede issue date")
        return self


class VolunteerExperience(Dated):
    type: Literal["volunteer_experience"] = "volunteer_experience"
    organization: Text
    title: Text
    location: str | None = None
    current: bool = False
    description: str = ""


class Award(Contract):
    type: Literal["award"] = "award"
    title: Text
    issuer: str | None = None
    date: DateValue | None = None
    description: str = ""


class Publication(Contract):
    type: Literal["publication"] = "publication"
    title: Text
    venue: str | None = None
    date: DateValue | None = None
    url: HttpUrl | None = None
    co_authors: list[Text] = Field(default_factory=list, max_length=100)


class CustomEntry(Contract):
    type: Literal["custom_entry"] = "custom_entry"
    entry_type: Literal["speaking", "patent", "other"] = "other"
    payload: dict[str, str] = Field(default_factory=dict)


CareerInput = Annotated[
    Experience
    | Project
    | Achievement
    | Education
    | Course
    | Skill
    | SkillEvidence
    | Certification
    | VolunteerExperience
    | Award
    | Publication
    | CustomEntry,
    Field(discriminator="type"),
]
CareerType = Literal[
    "experience",
    "project",
    "achievement",
    "education",
    "course",
    "skill",
    "skill_evidence",
    "certification",
    "volunteer_experience",
    "award",
    "publication",
    "custom_entry",
]


class CareerRecord(Contract):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    data: CareerInput


class FormField(Contract):
    name: str
    label: str
    input_type: Literal[
        "text", "date", "number", "checkbox", "select", "list", "details", "multiline"
    ]
    required: bool
    options: list[str] = Field(default_factory=list)
    related_type: CareerType | None = None
    default_value: str | bool | int | float | None = None


class CareerForm(Contract):
    type: CareerType
    fields: list[FormField]


INPUT_MODELS: list[type[Contract]] = [
    Experience,
    Project,
    Achievement,
    Education,
    Course,
    Skill,
    SkillEvidence,
    Certification,
    VolunteerExperience,
    Award,
    Publication,
    CustomEntry,
]
