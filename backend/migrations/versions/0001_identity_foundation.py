"""Identity foundation; no career or AI entities yet."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("password_hash", sa.String(512), nullable=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("user_id", "id", name="uq_users_owner_id"),
        sa.CheckConstraint("mode IN ('local', 'server')", name="ck_users_mode"),
        sa.CheckConstraint("user_id = id", name="ck_users_self_owner"),
    )
    op.create_index("ix_users_user_id", "users", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_users_user_id", table_name="users")
    op.drop_table("users")
