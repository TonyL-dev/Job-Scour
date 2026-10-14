from alembic import context

from app.ai import models as ai_models  # noqa: F401
from app.applications import models as applications_models  # noqa: F401
from app.ats import models as ats_models  # noqa: F401
from app.auth.models import User  # noqa: F401
from app.career import models as career_models  # noqa: F401
from app.core.config import get_settings
from app.core.database import Base, build_engine
from app.cover_letters import models as letter_models  # noqa: F401
from app.importers import models as import_models  # noqa: F401
from app.jobs import models as job_models  # noqa: F401
from app.profile import models as profile_models  # noqa: F401
from app.prompt_management import models as custom_prompt_models  # noqa: F401
from app.resumes import generation_models  # noqa: F401
from app.resumes import models as resume_models  # noqa: F401
from app.settings import models as settings_models  # noqa: F401
from app.templates import models as template_models  # noqa: F401

target_metadata = Base.metadata

if context.is_offline_mode():
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = build_engine(get_settings().database_url)
    with engine.connect() as connection:
        if engine.dialect.name == "sqlite":
            # Batch migrations rebuild referenced tables. Disable enforcement outside
            # the transaction and verify the entire migrated graph before reenabling.
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=engine.dialect.name == "sqlite",
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
        if engine.dialect.name == "sqlite":
            violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError("Migration produced invalid foreign keys")
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    engine.dispose()
