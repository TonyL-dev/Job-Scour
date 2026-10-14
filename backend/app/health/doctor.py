"""Read-only installation check; PDF uses synthetic content, never stored resumes."""

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import build_engine
from app.health.repository import database_ready
from app.privacy.repository import verify_store
from app.rendering.service import TEMPLATES, clear_cache, render
from app.resumes.schemas import ResumeDocument


def main() -> None:
    engine = build_engine(get_settings().database_url)
    try:
        with Session(engine) as db:
            if not database_ready(db):
                raise SystemExit("Database not ready. Run python scripts/tasks.py migrate.")
            verify_store(db)
        document = ResumeDocument.model_validate(
            {
                "schema_version": 1,
                "header": {"name": "Installation Check"},
                "sections": [],
                "metadata": {"template_id": str(TEMPLATES[0].id)},
            }
        )
        try:
            assert render(document).page_count == 1
        except Exception as error:
            raise SystemExit(
                "PDF check failed. Run renderer-setup; "
                "Linux also requires Chromium OS dependencies."
            ) from error
    finally:
        clear_cache()
        engine.dispose()
    print("PASS: migrated database, storage validation and real synthetic Chromium PDF")
    print("AI is optional; this check makes no model calls and does not verify Codex login.")


if __name__ == "__main__":
    main()
