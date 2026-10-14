"""Phase 6B user-confirmed profile evidence."""

import sqlalchemy as sa
from alembic import op

revision = "602b_profile"
down_revision = "601a_imports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "profile_reviews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id", "id"),
        sa.CheckConstraint("revision >= 1", name="ck_profile_review_revision"),
        sa.CheckConstraint(
            "status IN ('review','confirmed','discarded')", name="ck_profile_review_status"
        ),
    )
    op.create_index("ix_profile_reviews_user_id", "profile_reviews", ["user_id"])


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM profile_reviews")):
        raise RuntimeError("Refusing to discard profile evidence history")
    op.drop_table("profile_reviews")
