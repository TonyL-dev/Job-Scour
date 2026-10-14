from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, OwnedRecord
from app.core.encryption import SecureJSON, SecureText


class Resume(OwnedRecord, Base):
    __tablename__ = "resume_documents"
    __table_args__ = (
        UniqueConstraint("user_id", "id", name="uq_resumes_owner_id"),
        ForeignKeyConstraint(
            ["user_id", "parent_document_id"],
            ["resume_documents.user_id", "resume_documents.id"],
            name="fk_resume_parent",
        ),
        CheckConstraint("version_number >= 0", name="ck_resume_version"),
        CheckConstraint("kind IN ('master', 'tailored')", name="ck_resume_kind"),
        Index(
            "uq_master_gold_standard",
            "user_id",
            unique=True,
            sqlite_where=text("gold_standard = 1"),
            postgresql_where=text("gold_standard"),
        ),
    )
    parent_document_id: Mapped[UUID | None] = mapped_column(Uuid)
    title: Mapped[str] = mapped_column(SecureText("resume_documents.title"))
    kind: Mapped[str] = mapped_column(String(16), default="master")
    version_number: Mapped[int] = mapped_column(Integer, default=0)
    gold_standard: Mapped[bool] = mapped_column(Boolean, default=False)


class Version(OwnedRecord, Base):
    __tablename__ = "resume_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "document_id"],
            ["resume_documents.user_id", "resume_documents.id"],
            name="fk_version_document",
        ),
        UniqueConstraint("user_id", "document_id", "version_number", name="uq_resume_version"),
        CheckConstraint("version_number > 0", name="ck_version_positive"),
        UniqueConstraint("user_id", "id", name="uq_version_owner_id"),
        ForeignKeyConstraint(
            ["user_id", "restored_from_version_id"],
            ["resume_versions.user_id", "resume_versions.id"],
            name="fk_restored_version",
        ),
        CheckConstraint(
            "change_kind IN ('user','autosave','restore','duplicate','ai')",
            name="ck_version_change_kind",
        ),
    )
    change_kind: Mapped[str] = mapped_column(String(16), default="user", server_default="user")
    restored_from_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    document_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    content_snapshot: Mapped[dict[str, object]] = mapped_column(
        SecureJSON("resume_versions.content_snapshot")
    )
    content_hash: Mapped[str] = mapped_column(String(64))
