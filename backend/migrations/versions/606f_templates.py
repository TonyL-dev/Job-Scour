"""Phase 6F immutable templates and encrypted local assets."""

import sqlalchemy as sa
from alembic import op

revision = "606f_templates"
down_revision = "604d_prompts"
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
        "custom_templates",
        *owned(),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("latest_revision", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("user_id", "id"),
    )
    op.create_table(
        "custom_template_versions",
        *owned(),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id", "id"),
        sa.UniqueConstraint("user_id", "document_id", "revision"),
        sa.ForeignKeyConstraint(
            ["user_id", "document_id"], ["custom_templates.user_id", "custom_templates.id"]
        ),
    )
    op.create_table(
        "template_assets",
        *owned(),
        sa.Column("ciphertext", sa.Text(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.UniqueConstraint("user_id", "id"),
    )
    for table in ("custom_templates", "custom_template_versions", "template_assets"):
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM custom_templates")):
        raise RuntimeError("Refusing to discard custom template versions")
    op.drop_table("custom_template_versions")
    op.drop_table("custom_templates")
    op.drop_table("template_assets")
