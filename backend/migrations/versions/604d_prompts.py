"""Phase 6D immutable prompt preferences and evaluation gates."""

import sqlalchemy as sa
from alembic import op

revision = "604d_prompts"
down_revision = "603c_letters"
branch_labels = None
depends_on = None


def owned() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "custom_prompts",
        *owned(),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("digest", sa.Text(), nullable=False),
        sa.Column("base_digest", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id", "id"),
    )
    op.create_table(
        "prompt_evaluations",
        *owned(),
        sa.Column("prompt_id", sa.Uuid(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("configuration_digest", sa.Text(), nullable=False),
        sa.Column("results", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id", "id"),
        sa.ForeignKeyConstraint(
            ["user_id", "prompt_id"], ["custom_prompts.user_id", "custom_prompts.id"]
        ),
    )
    op.create_table(
        "active_custom_prompts",
        *owned(),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("prompt_id", sa.Uuid(), nullable=False),
        sa.UniqueConstraint("user_id", "task"),
        sa.ForeignKeyConstraint(
            ["user_id", "prompt_id"], ["custom_prompts.user_id", "custom_prompts.id"]
        ),
    )
    for table in ("custom_prompts", "prompt_evaluations", "active_custom_prompts"):
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM custom_prompts")):
        raise RuntimeError("Refusing to discard prompt history")
    op.drop_table("active_custom_prompts")
    op.drop_table("prompt_evaluations")
    op.drop_table("custom_prompts")
