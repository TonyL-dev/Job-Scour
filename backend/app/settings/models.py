from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKeyConstraint,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, OwnedRecord


class LLMEndpoint(OwnedRecord, Base):
    __tablename__ = "llm_endpoints"
    __table_args__ = (
        UniqueConstraint("user_id", "id"),
        CheckConstraint(
            "provider IN ('codex', 'lm_studio', 'ollama', 'openai_compatible')",
            name="ck_llm_provider",
        ),
    )
    name: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(Text)
    base_url: Mapped[str] = mapped_column(Text)
    remote_consent: Mapped[bool] = mapped_column(Boolean)
    enabled: Mapped[bool] = mapped_column(Boolean)
    api_key_env: Mapped[str | None] = mapped_column(Text)


class ModelProfile(OwnedRecord, Base):
    __tablename__ = "model_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "id"),
        CheckConstraint(
            "context_window >= 512 AND max_output_tokens >= 32 "
            "AND max_output_tokens < context_window",
            name="ck_profile_budget",
        ),
        CheckConstraint(
            "temperature >= 0 AND temperature <= 2 AND top_p > 0 AND top_p <= 1",
            name="ck_profile_sampling",
        ),
        CheckConstraint(
            "structured_mode IN ('json_schema', 'json_object', 'none')",
            name="ck_profile_structured_mode",
        ),
        ForeignKeyConstraint(
            ["user_id", "endpoint_id"], ["llm_endpoints.user_id", "llm_endpoints.id"]
        ),
    )
    endpoint_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    model: Mapped[str] = mapped_column(Text)
    context_window: Mapped[int] = mapped_column(Integer)
    max_output_tokens: Mapped[int] = mapped_column(Integer)
    temperature: Mapped[float] = mapped_column(Float)
    top_p: Mapped[float] = mapped_column(Float)
    structured_mode: Mapped[str] = mapped_column(Text)


class TaskAssignment(OwnedRecord, Base):
    __tablename__ = "task_model_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", "task"),
        CheckConstraint(
            "task IN ('job_analysis', 'embeddings', 'ranking', 'rewriting', "
            "'summary', 'verification', 'condensing', 'import_extraction', "
            "'profile_questions', 'cover_letter')",
            name="ck_assignment_task",
        ),
        ForeignKeyConstraint(
            ["user_id", "profile_id"], ["model_profiles.user_id", "model_profiles.id"]
        ),
    )
    task: Mapped[str] = mapped_column(Text)
    profile_id: Mapped[UUID] = mapped_column(Uuid, index=True)
