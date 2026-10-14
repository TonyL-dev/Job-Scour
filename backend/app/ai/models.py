from uuid import UUID

from sqlalchemy import Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, OwnedRecord
from app.core.encryption import SecureJSON, SecureText


class PromptVersion(OwnedRecord, Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (UniqueConstraint("user_id", "key", "version", "digest"),)
    key: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(Text)
    digest: Mapped[str] = mapped_column(Text)
    system_text: Mapped[str] = mapped_column(SecureText("prompt_versions.system_text"))
    user_template: Mapped[str] = mapped_column(SecureText("prompt_versions.user_template"))


class Embedding(OwnedRecord, Base):
    __tablename__ = "embeddings"
    __table_args__ = (
        UniqueConstraint("user_id", "entity_type", "entity_id", "model_key", "content_hash"),
    )
    entity_type: Mapped[str] = mapped_column(Text)
    entity_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    model_key: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(Text)
    vector: Mapped[list[float]] = mapped_column(SecureJSON("embeddings.vector"))
