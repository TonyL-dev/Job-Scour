from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Integer, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, OwnedRecord
from app.core.encryption import SecureJSON, SecureText


class LetterDocument(OwnedRecord, Base):
    __tablename__ = "cover_letters"
    __table_args__ = (
        UniqueConstraint("user_id", "id"),
        ForeignKeyConstraint(
            ["user_id", "job_id"], ["job_descriptions.user_id", "job_descriptions.id"]
        ),
    )
    title: Mapped[str] = mapped_column(SecureText("cover.title"))
    job_id: Mapped[UUID] = mapped_column(Uuid)
    latest_version: Mapped[int] = mapped_column(Integer, default=1)


class LetterSnapshot(OwnedRecord, Base):
    __tablename__ = "cover_letter_versions"
    __table_args__ = (
        UniqueConstraint("user_id", "id"),
        UniqueConstraint("user_id", "document_id", "version_number"),
        ForeignKeyConstraint(
            ["user_id", "document_id"], ["cover_letters.user_id", "cover_letters.id"]
        ),
        CheckConstraint("version_number >= 1", name="ck_cover_version"),
    )
    document_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, object]] = mapped_column(SecureJSON("cover.snapshot"))


class LetterOperation(OwnedRecord, Base):
    __tablename__ = "cover_letter_runs"
    __table_args__ = (
        UniqueConstraint("user_id", "id"),
        CheckConstraint("revision >= 1", name="ck_cover_run_revision"),
        CheckConstraint(
            "status IN ('queued','running','review','failed','cancelled','committed')",
            name="ck_cover_run_status",
        ),
        ForeignKeyConstraint(
            ["user_id", "saved_version_id"],
            ["cover_letter_versions.user_id", "cover_letter_versions.id"],
        ),
    )
    revision: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(Text, default="queued")
    payload: Mapped[dict[str, object]] = mapped_column(SecureJSON("cover.run"))
    saved_version_id: Mapped[UUID | None] = mapped_column(Uuid)
