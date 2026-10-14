from sqlalchemy import CheckConstraint, Integer, LargeBinary, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, OwnedRecord
from app.core.encryption import SecureJSON, SecureText


class ImportRecord(OwnedRecord, Base):
    __tablename__ = "import_runs"
    __table_args__ = (
        UniqueConstraint("user_id", "id"),
        CheckConstraint("revision >= 1", name="ck_import_revision"),
        CheckConstraint(
            "status IN ('parsing','failed','review','committed','discarded')",
            name="ck_import_status",
        ),
    )
    filename: Mapped[str] = mapped_column(SecureText("import.filename"))
    mime: Mapped[str] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(Text, default="review")
    payload: Mapped[dict[str, object]] = mapped_column(SecureJSON("import.payload"))
    original: Mapped[bytes | None] = mapped_column(LargeBinary)
