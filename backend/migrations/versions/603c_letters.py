"""Phase 6C cover letters and exact submitted version links."""

import sqlalchemy as sa
from alembic import op

revision = "603c_letters"
down_revision = "602b_profile"
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
        "cover_letters",
        *owned(),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("latest_version", sa.Integer(), nullable=False),
        sa.UniqueConstraint("user_id", "id"),
        sa.ForeignKeyConstraint(
            ["user_id", "job_id"], ["job_descriptions.user_id", "job_descriptions.id"]
        ),
    )
    op.create_table(
        "cover_letter_versions",
        *owned(),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id", "id"),
        sa.UniqueConstraint("user_id", "document_id", "version_number"),
        sa.CheckConstraint("version_number >= 1", name="ck_cover_version"),
        sa.ForeignKeyConstraint(
            ["user_id", "document_id"], ["cover_letters.user_id", "cover_letters.id"]
        ),
    )
    op.create_table(
        "cover_letter_runs",
        *owned(),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("saved_version_id", sa.Uuid(), nullable=True),
        sa.UniqueConstraint("user_id", "id"),
        sa.CheckConstraint("revision >= 1", name="ck_cover_run_revision"),
        sa.CheckConstraint(
            "status IN ('queued','running','review','failed','cancelled','committed')",
            name="ck_cover_run_status",
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "saved_version_id"],
            ["cover_letter_versions.user_id", "cover_letter_versions.id"],
        ),
    )
    for table in ("cover_letters", "cover_letter_versions", "cover_letter_runs"):
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])
    op.create_index(
        "ix_cover_letter_versions_document_id", "cover_letter_versions", ["document_id"]
    )
    with op.batch_alter_table("applications") as batch:
        batch.add_column(sa.Column("cover_letter_version_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_application_cover_version",
            "cover_letter_versions",
            ["user_id", "cover_letter_version_id"],
            ["user_id", "id"],
        )


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM cover_letters")):
        raise RuntimeError("Refusing to discard saved letters")
    with op.batch_alter_table("applications") as batch:
        batch.drop_constraint("fk_application_cover_version", type_="foreignkey")
        batch.drop_column("cover_letter_version_id")
    op.drop_table("cover_letter_runs")
    op.drop_table("cover_letter_versions")
    op.drop_table("cover_letters")
