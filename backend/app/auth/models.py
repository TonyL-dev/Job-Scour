from sqlalchemy import CheckConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, OwnedRecord


class User(OwnedRecord, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("mode IN ('local', 'server')", name="ck_users_mode"),
        CheckConstraint("user_id = id", name="ck_users_self_owner"),
        UniqueConstraint("user_id", "id", name="uq_users_owner_id"),
    )

    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(512))
    display_name: Mapped[str] = mapped_column(String(200))
    mode: Mapped[str] = mapped_column(String(16), default="local")
