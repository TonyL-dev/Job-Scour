from uuid import UUID

from sqlalchemy import Boolean, ForeignKeyConstraint, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, OwnedRecord
from app.core.encryption import SecureJSON, SecureText


class JobDescription(OwnedRecord, Base):
    __tablename__ = "job_descriptions"
    __table_args__ = (UniqueConstraint("user_id", "id"),)
    company: Mapped[str] = mapped_column(SecureText("job_descriptions.company"))
    title: Mapped[str] = mapped_column(SecureText("job_descriptions.title"))
    location: Mapped[str] = mapped_column(SecureText("job_descriptions.location"))
    url: Mapped[str] = mapped_column(SecureText("job_descriptions.url"))
    raw_text: Mapped[str] = mapped_column(SecureText("job_descriptions.raw_text"))


class AnalysisRecord(OwnedRecord, Base):
    __tablename__ = "job_analyses"
    __table_args__ = (
        UniqueConstraint("user_id", "id"),
        ForeignKeyConstraint(
            ["user_id", "job_id"], ["job_descriptions.user_id", "job_descriptions.id"]
        ),
    )
    job_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    fingerprint: Mapped[str] = mapped_column(Text, index=True)
    model: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(Text)
    result: Mapped[dict[str, object]] = mapped_column(SecureJSON("job_analyses.result"))


class MatchRecord(OwnedRecord, Base):
    __tablename__ = "match_analyses"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "analysis_id"], ["job_analyses.user_id", "job_analyses.id"]
        ),
    )
    analysis_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    result: Mapped[dict[str, object]] = mapped_column(SecureJSON("match_analyses.result"))
    cached: Mapped[bool] = mapped_column(Boolean)
