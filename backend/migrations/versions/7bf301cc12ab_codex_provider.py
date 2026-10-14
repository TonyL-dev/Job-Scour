"""Codex CLI provider; existing endpoints and consent remain unchanged."""

from alembic import op

revision = "7bf301cc12ab"
down_revision = "3fa6b17e6fda"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("llm_endpoints") as batch:
        batch.drop_constraint("ck_llm_provider", type_="check")
        batch.create_check_constraint(
            "ck_llm_provider", "provider IN ('codex', 'lm_studio', 'ollama', 'openai_compatible')"
        )


def downgrade() -> None:
    from sqlalchemy import text

    if op.get_bind().execute(text("SELECT 1 FROM llm_endpoints WHERE provider = 'codex'")).first():
        raise RuntimeError("Remove Codex endpoints and their profiles before downgrading")
    with op.batch_alter_table("llm_endpoints") as batch:
        batch.drop_constraint("ck_llm_provider", type_="check")
        batch.create_check_constraint(
            "ck_llm_provider", "provider IN ('lm_studio', 'ollama', 'openai_compatible')"
        )
