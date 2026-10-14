from datetime import date as DateValue
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, OwnedRecord
from app.core.encryption import SecureIndex, SecureJSON, SecureText


class CareerBase(OwnedRecord, Base):
    __abstract__ = True
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Experience(CareerBase):
    __tablename__ = "experiences"
    __table_args__ = (
        UniqueConstraint("user_id", "id", name="uq_experiences_owner_id"),
        CheckConstraint(
            "employment_type IN ('full_time', 'part_time', 'contract', 'internship', 'freelance', "
            "'other')",
            name="ck_experiences_employment_type",
        ),
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="ck_experiences_dates",
        ),
        CheckConstraint("NOT current OR end_date IS NULL", name="ck_experiences_current"),
    )
    start_date: Mapped[DateValue] = mapped_column(Date)
    end_date: Mapped[DateValue | None] = mapped_column(Date)
    company: Mapped[str] = mapped_column(SecureText("experiences.company"))
    job_title: Mapped[str] = mapped_column(SecureText("experiences.job_title"))
    location: Mapped[str | None] = mapped_column(SecureText("experiences.location"))
    employment_type: Mapped[str] = mapped_column(Text)
    current: Mapped[bool] = mapped_column(Boolean)
    description: Mapped[str] = mapped_column(SecureText("experiences.description"))
    industry: Mapped[str | None] = mapped_column(SecureText("experiences.industry"))
    ordering_hint: Mapped[int] = mapped_column(Integer)


class Project(CareerBase):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("user_id", "id", name="uq_projects_owner_id"),
        ForeignKeyConstraint(
            ["user_id", "experience_id"],
            ["experiences.user_id", "experiences.id"],
            name="fk_projects_experience_id",
        ),
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="ck_projects_dates",
        ),
    )
    start_date: Mapped[DateValue | None] = mapped_column(Date)
    end_date: Mapped[DateValue | None] = mapped_column(Date)
    experience_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    name: Mapped[str] = mapped_column(SecureText("projects.name"))
    description: Mapped[str] = mapped_column(SecureText("projects.description"))
    role: Mapped[str | None] = mapped_column(SecureText("projects.role"))
    url: Mapped[str | None] = mapped_column(SecureText("projects.url"))
    challenges_solved: Mapped[str] = mapped_column(SecureText("projects.challenges_solved"))
    results: Mapped[str] = mapped_column(SecureText("projects.results"))


class Achievement(CareerBase):
    __tablename__ = "achievements"
    __table_args__ = (
        UniqueConstraint("user_id", "id", name="uq_achievements_owner_id"),
        ForeignKeyConstraint(
            ["user_id", "experience_id"],
            ["experiences.user_id", "experiences.id"],
            name="fk_achievements_experience_id",
        ),
        ForeignKeyConstraint(
            ["user_id", "project_id"],
            ["projects.user_id", "projects.id"],
            name="fk_achievements_project_id",
        ),
        CheckConstraint(
            "category IN ('responsibility', 'achievement', 'impact')",
            name="ck_achievements_category",
        ),
        CheckConstraint(
            "(experience_id IS NOT NULL AND project_id IS NULL) "
            "OR (experience_id IS NULL AND project_id IS NOT NULL)",
            name="ck_achievements_parent",
        ),
        CheckConstraint("importance BETWEEN 1 AND 5", name="ck_achievements_importance"),
    )
    experience_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    project_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    text: Mapped[str] = mapped_column(SecureText("achievements.text"))
    category: Mapped[str] = mapped_column(Text)
    metric_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    metric_unit: Mapped[str | None] = mapped_column(SecureText("achievements.metric_unit"))
    metric_description: Mapped[str | None] = mapped_column(
        SecureText("achievements.metric_description")
    )
    verified_by_user: Mapped[bool] = mapped_column(Boolean)
    importance: Mapped[int] = mapped_column(Integer)


class Education(CareerBase):
    __tablename__ = "education"
    __table_args__ = (
        UniqueConstraint("user_id", "id", name="uq_education_owner_id"),
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="ck_education_dates",
        ),
    )
    start_date: Mapped[DateValue | None] = mapped_column(Date)
    end_date: Mapped[DateValue | None] = mapped_column(Date)
    institution: Mapped[str] = mapped_column(SecureText("education.institution"))
    degree: Mapped[str] = mapped_column(SecureText("education.degree"))
    field: Mapped[str | None] = mapped_column(SecureText("education.field"))
    gpa: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    honors: Mapped[str | None] = mapped_column(SecureText("education.honors"))


class Course(CareerBase):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("user_id", "id", name="uq_courses_owner_id"),
        ForeignKeyConstraint(
            ["user_id", "education_id"],
            ["education.user_id", "education.id"],
            name="fk_courses_education_id",
        ),
    )
    education_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    name: Mapped[str] = mapped_column(SecureText("courses.name"))
    description: Mapped[str] = mapped_column(SecureText("courses.description"))


class Skill(CareerBase):
    __tablename__ = "skills"
    __table_args__ = (
        UniqueConstraint("user_id", "id", name="uq_skills_owner_id"),
        CheckConstraint(
            "category IN ('language', 'framework', 'tool', 'soft_skill', 'domain')",
            name="ck_skills_category",
        ),
        CheckConstraint(
            "proficiency IN ('beginner', 'intermediate', 'advanced', 'expert')",
            name="ck_skills_proficiency",
        ),
        UniqueConstraint("user_id", "normalized_name", name="uq_skills_name"),
        CheckConstraint("years_of_use IS NULL OR years_of_use >= 0", name="ck_skills_years"),
    )
    name: Mapped[str] = mapped_column(SecureText("skills.name"))
    category: Mapped[str] = mapped_column(Text)
    proficiency: Mapped[str | None] = mapped_column(Text)
    years_of_use: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    last_used_date: Mapped[DateValue | None] = mapped_column(Date)
    aliases: Mapped[list[str]] = mapped_column(SecureJSON("skills.aliases"))
    normalized_name: Mapped[str] = mapped_column(SecureIndex())


class SkillEvidence(CareerBase):
    __tablename__ = "skill_evidence"
    __table_args__ = (
        UniqueConstraint("user_id", "id", name="uq_skill_evidence_owner_id"),
        ForeignKeyConstraint(
            ["user_id", "skill_id"],
            ["skills.user_id", "skills.id"],
            name="fk_skill_evidence_skill_id",
        ),
        ForeignKeyConstraint(
            ["user_id", "experience_id"],
            ["experiences.user_id", "experiences.id"],
            name="fk_skill_evidence_experience_id",
        ),
        ForeignKeyConstraint(
            ["user_id", "project_id"],
            ["projects.user_id", "projects.id"],
            name="fk_skill_evidence_project_id",
        ),
        ForeignKeyConstraint(
            ["user_id", "achievement_id"],
            ["achievements.user_id", "achievements.id"],
            name="fk_skill_evidence_achievement_id",
        ),
        CheckConstraint(
            "CASE WHEN experience_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN project_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN achievement_id IS NULL THEN 0 ELSE 1 END = 1",
            name="ck_evidence_target",
        ),
        UniqueConstraint("user_id", "skill_id", "experience_id", name="uq_evidence_experience_id"),
        UniqueConstraint("user_id", "skill_id", "project_id", name="uq_evidence_project_id"),
        UniqueConstraint(
            "user_id", "skill_id", "achievement_id", name="uq_evidence_achievement_id"
        ),
    )
    skill_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    experience_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    project_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    achievement_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)


class Certification(CareerBase):
    __tablename__ = "certifications"
    __table_args__ = (
        UniqueConstraint("user_id", "id", name="uq_certifications_owner_id"),
        CheckConstraint(
            "expiry_date IS NULL OR issue_date IS NULL OR expiry_date >= issue_date",
            name="ck_certifications_dates",
        ),
    )
    name: Mapped[str] = mapped_column(SecureText("certifications.name"))
    issuer: Mapped[str] = mapped_column(SecureText("certifications.issuer"))
    issue_date: Mapped[DateValue | None] = mapped_column(Date)
    expiry_date: Mapped[DateValue | None] = mapped_column(Date)
    credential_id: Mapped[str | None] = mapped_column(SecureText("certifications.credential_id"))
    url: Mapped[str | None] = mapped_column(SecureText("certifications.url"))


class VolunteerExperience(CareerBase):
    __tablename__ = "volunteer_experiences"
    __table_args__ = (
        UniqueConstraint("user_id", "id", name="uq_volunteer_experiences_owner_id"),
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="ck_volunteer_experiences_dates",
        ),
        CheckConstraint("NOT current OR end_date IS NULL", name="ck_volunteer_experiences_current"),
    )
    start_date: Mapped[DateValue | None] = mapped_column(Date)
    end_date: Mapped[DateValue | None] = mapped_column(Date)
    organization: Mapped[str] = mapped_column(SecureText("volunteer_experiences.organization"))
    title: Mapped[str] = mapped_column(SecureText("volunteer_experiences.title"))
    location: Mapped[str | None] = mapped_column(SecureText("volunteer_experiences.location"))
    current: Mapped[bool] = mapped_column(Boolean)
    description: Mapped[str] = mapped_column(SecureText("volunteer_experiences.description"))


class Award(CareerBase):
    __tablename__ = "awards"
    __table_args__ = (UniqueConstraint("user_id", "id", name="uq_awards_owner_id"),)
    title: Mapped[str] = mapped_column(SecureText("awards.title"))
    issuer: Mapped[str | None] = mapped_column(SecureText("awards.issuer"))
    date: Mapped[DateValue | None] = mapped_column(Date)
    description: Mapped[str] = mapped_column(SecureText("awards.description"))


class Publication(CareerBase):
    __tablename__ = "publications"
    __table_args__ = (UniqueConstraint("user_id", "id", name="uq_publications_owner_id"),)
    title: Mapped[str] = mapped_column(SecureText("publications.title"))
    venue: Mapped[str | None] = mapped_column(SecureText("publications.venue"))
    date: Mapped[DateValue | None] = mapped_column(Date)
    url: Mapped[str | None] = mapped_column(SecureText("publications.url"))
    co_authors: Mapped[list[str]] = mapped_column(SecureJSON("publications.co_authors"))


class CustomEntry(CareerBase):
    __tablename__ = "custom_entries"
    __table_args__ = (
        UniqueConstraint("user_id", "id", name="uq_custom_entries_owner_id"),
        CheckConstraint(
            "entry_type IN ('speaking', 'patent', 'other')", name="ck_custom_entries_entry_type"
        ),
    )
    entry_type: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, str]] = mapped_column(SecureJSON("custom_entries.payload"))


MODELS: dict[str, type[CareerBase]] = {
    "experience": Experience,
    "project": Project,
    "achievement": Achievement,
    "education": Education,
    "course": Course,
    "skill": Skill,
    "skill_evidence": SkillEvidence,
    "certification": Certification,
    "volunteer_experience": VolunteerExperience,
    "award": Award,
    "publication": Publication,
    "custom_entry": CustomEntry,
}
