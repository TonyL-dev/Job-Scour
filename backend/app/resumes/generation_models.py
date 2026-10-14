from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, OwnedRecord
from app.core.encryption import SecureJSON, SecureText


class GenerationRecord(OwnedRecord, Base):
    __tablename__ = "generation_runs"
    __table_args__ = (
        UniqueConstraint("user_id", "id", name="uq_generation_owner_id"),
        ForeignKeyConstraint(
            ["user_id", "master_id"], ["resume_documents.user_id", "resume_documents.id"]
        ),
        ForeignKeyConstraint(
            ["user_id", "job_id"], ["job_descriptions.user_id", "job_descriptions.id"]
        ),
        ForeignKeyConstraint(
            ["user_id", "saved_resume_id"], ["resume_documents.user_id", "resume_documents.id"]
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_generation_status",
        ),
        ForeignKeyConstraint(
            ["user_id", "saved_version_id"],
            ["resume_versions.user_id", "resume_versions.id"],
            name="fk_generation_saved_version",
        ),
        CheckConstraint("review_revision >= 0", name="ck_generation_revision"),
    )
    master_id: Mapped[UUID] = mapped_column(Uuid)
    job_id: Mapped[UUID] = mapped_column(Uuid)
    saved_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    saved_resume_id: Mapped[UUID | None] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(Text)
    request_snapshot: Mapped[dict[str, object]] = mapped_column(
        SecureJSON("generation_runs.request_snapshot")
    )
    base_snapshot: Mapped[dict[str, object]] = mapped_column(
        SecureJSON("generation_runs.base_snapshot")
    )
    proposed_snapshot: Mapped[dict[str, object] | None] = mapped_column(
        SecureJSON("generation_runs.proposed_snapshot")
    )
    events: Mapped[list[dict[str, object]]] = mapped_column(
        SecureJSON("generation_runs.events"), default=list
    )
    warnings: Mapped[list[str]] = mapped_column(
        SecureJSON("generation_runs.warnings"), default=list
    )
    provenance: Mapped[dict[str, str]] = mapped_column(
        SecureJSON("generation_runs.provenance"), default=dict
    )
    decisions: Mapped[list[dict[str, object]]] = mapped_column(
        SecureJSON("generation_runs.decisions"), default=list
    )
    suggestion_ids: Mapped[list[str]] = mapped_column(
        SecureJSON("generation_runs.suggestion_ids"), default=list
    )
    review_locks: Mapped[dict[str, bool]] = mapped_column(
        SecureJSON("generation_runs.review_locks"), default=dict
    )
    page_count: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(SecureText("generation_runs.error"))
    review_revision: Mapped[int] = mapped_column(Integer, default=0)


class SuggestionRecord(OwnedRecord, Base):
    __tablename__ = "generation_suggestions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "run_id"], ["generation_runs.user_id", "generation_runs.id"]
        ),
    )
    run_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    snapshot: Mapped[dict[str, object]] = mapped_column(
        SecureJSON("generation_suggestions.snapshot")
    )
