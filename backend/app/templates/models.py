from uuid import UUID

from sqlalchemy import Boolean, ForeignKeyConstraint, Integer, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, OwnedRecord
from app.core.encryption import SecureJSON, SecureText


class TemplateDocument(OwnedRecord, Base):
    __tablename__ = "custom_templates"
    __table_args__ = (UniqueConstraint("user_id", "id"),)
    name: Mapped[str] = mapped_column(SecureText("template.name"))
    latest_revision: Mapped[int] = mapped_column(Integer, default=1)
    retired: Mapped[bool] = mapped_column(Boolean, default=False)


class TemplateRevision(OwnedRecord, Base):
    __tablename__ = "custom_template_versions"
    __table_args__ = (
        UniqueConstraint("user_id", "id"),
        UniqueConstraint("user_id", "document_id", "revision"),
        ForeignKeyConstraint(
            ["user_id", "document_id"], ["custom_templates.user_id", "custom_templates.id"]
        ),
    )
    document_id: Mapped[UUID] = mapped_column(Uuid)
    revision: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, object]] = mapped_column(SecureJSON("template.snapshot"))


class TemplateAsset(OwnedRecord, Base):
    __tablename__ = "template_assets"
    __table_args__ = (UniqueConstraint("user_id", "id"),)
    ciphertext: Mapped[str] = mapped_column(Text)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
