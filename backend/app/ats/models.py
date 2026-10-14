from uuid import UUID

from sqlalchemy import ForeignKeyConstraint, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, OwnedRecord
from app.core.encryption import SecureJSON


class ATSReport(OwnedRecord, Base):
    __tablename__ = "ats_reports"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "version_id"], ["resume_versions.user_id", "resume_versions.id"]
        ),
        ForeignKeyConstraint(
            ["user_id", "analysis_id"], ["job_analyses.user_id", "job_analyses.id"]
        ),
    )
    version_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    analysis_id: Mapped[UUID | None] = mapped_column(Uuid)
    engine_version: Mapped[str] = mapped_column(Text)
    result: Mapped[dict[str, object]] = mapped_column(SecureJSON("ats_reports.result"))
