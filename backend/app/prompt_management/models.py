from uuid import UUID

from sqlalchemy import Boolean, ForeignKeyConstraint, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, OwnedRecord
from app.core.encryption import SecureJSON


class PromptCustomization(OwnedRecord, Base):
    __tablename__ = "custom_prompts"
    __table_args__ = (UniqueConstraint("user_id", "id"),)
    task: Mapped[str] = mapped_column(Text)
    digest: Mapped[str] = mapped_column(Text)
    base_digest: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, object]] = mapped_column(SecureJSON("prompt.custom"))


class PromptEvaluation(OwnedRecord, Base):
    __tablename__ = "prompt_evaluations"
    __table_args__ = (
        UniqueConstraint("user_id", "id"),
        ForeignKeyConstraint(
            ["user_id", "prompt_id"], ["custom_prompts.user_id", "custom_prompts.id"]
        ),
    )
    prompt_id: Mapped[UUID] = mapped_column(Uuid)
    passed: Mapped[bool] = mapped_column(Boolean)
    configuration_digest: Mapped[str] = mapped_column(Text)
    results: Mapped[list[dict[str, object]]] = mapped_column(SecureJSON("prompt.evaluation"))


class ActivePrompt(OwnedRecord, Base):
    __tablename__ = "active_custom_prompts"
    __table_args__ = (
        UniqueConstraint("user_id", "task"),
        ForeignKeyConstraint(
            ["user_id", "prompt_id"], ["custom_prompts.user_id", "custom_prompts.id"]
        ),
    )
    task: Mapped[str] = mapped_column(Text)
    prompt_id: Mapped[UUID] = mapped_column(Uuid)
