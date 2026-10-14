from datetime import date as DateValue
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKeyConstraint,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, OwnedRecord
from app.core.encryption import SecureText


class ApplicationRecord(OwnedRecord, Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "id"),
        ForeignKeyConstraint(
            ["user_id", "version_id"], ["resume_versions.user_id", "resume_versions.id"]
        ),
        ForeignKeyConstraint(
            ["user_id", "job_id"], ["job_descriptions.user_id", "job_descriptions.id"]
        ),
        ForeignKeyConstraint(
            ["user_id", "cover_letter_version_id"],
            ["cover_letter_versions.user_id", "cover_letter_versions.id"],
        ),
        CheckConstraint(
            "stage IN ('saved','applied','screen','interview','offer','rejected','withdrawn')",
            name="ck_application_stage",
        ),
        CheckConstraint("revision > 0", name="ck_application_revision"),
    )
    company: Mapped[str] = mapped_column(SecureText("applications.company"))
    position: Mapped[str] = mapped_column(SecureText("applications.position"))
    version_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    cover_letter_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    job_id: Mapped[UUID | None] = mapped_column(Uuid)
    date_applied: Mapped[DateValue | None] = mapped_column(Date, index=True)
    stage: Mapped[str] = mapped_column(Text, index=True)
    channel: Mapped[str] = mapped_column(SecureText("applications.channel"))
    notes: Mapped[str] = mapped_column(SecureText("applications.notes"))
    follow_up_date: Mapped[DateValue | None] = mapped_column(Date)
    follow_up_done: Mapped[bool] = mapped_column(Boolean)
    revision: Mapped[int] = mapped_column(Integer, default=1)


class EventRecord(OwnedRecord, Base):
    __tablename__ = "application_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "application_id"], ["applications.user_id", "applications.id"]
        ),
        CheckConstraint(
            "stage IN ('saved','applied','screen','interview','offer','rejected','withdrawn')",
            name="ck_event_stage",
        ),
    )
    application_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    stage: Mapped[str] = mapped_column(Text)
    date: Mapped[DateValue] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(SecureText("application_events.notes"))
