"""Phase 6A staged import review and explicit model task assignment."""

import sqlalchemy as sa
from alembic import op

revision = "601a_imports"
down_revision = "20d2f08208c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("mime", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("original", sa.LargeBinary(), nullable=True),
        sa.UniqueConstraint("user_id", "id"),
        sa.CheckConstraint("revision >= 1", name="ck_import_revision"),
        sa.CheckConstraint(
            "status IN ('parsing','failed','review','committed','discarded')",
            name="ck_import_status",
        ),
    )
    op.create_index("ix_import_runs_user_id", "import_runs", ["user_id"])
    with op.batch_alter_table("task_model_assignments") as batch:
        batch.drop_constraint("ck_assignment_task", type_="check")
        batch.create_check_constraint(
            "ck_assignment_task",
            "task IN ('job_analysis','embeddings','ranking','rewriting','summary',"
            "'verification','condensing','import_extraction','profile_questions','cover_letter')",
        )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT COUNT(*) FROM import_runs")):
        raise RuntimeError("Refusing to discard populated import reviews")
    if connection.scalar(
        sa.text(
            "SELECT COUNT(*) FROM task_model_assignments "
            "WHERE task IN ('import_extraction','profile_questions','cover_letter')"
        )
    ):
        raise RuntimeError("Remove Phase 6 assignments before downgrade")
    with op.batch_alter_table("task_model_assignments") as batch:
        batch.drop_constraint("ck_assignment_task", type_="check")
        batch.create_check_constraint(
            "ck_assignment_task",
            "task IN ('job_analysis','embeddings','ranking','rewriting','summary',"
            "'verification','condensing')",
        )
    op.drop_table("import_runs")
