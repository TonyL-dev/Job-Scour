from sqlalchemy import CheckConstraint, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, OwnedRecord
from app.core.encryption import SecureJSON


class ProfileRun(OwnedRecord, Base):
    __tablename__ = "profile_reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "id"),
        CheckConstraint("revision >= 1", name="ck_profile_review_revision"),
        CheckConstraint(
            "status IN ('review','confirmed','discarded')", name="ck_profile_review_status"
        ),
    )
    revision: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(Text, default="review")
    payload: Mapped[dict[str, object]] = mapped_column(SecureJSON("profile.review"))
