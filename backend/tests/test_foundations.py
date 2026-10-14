from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.config import Settings
from app.core.database import build_engine
from app.main import create_app


@pytest.fixture
def database_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("APP_DATABASE_URL", url)
    from app.core.config import get_settings

    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    yield url
    get_settings.cache_clear()


def test_health_and_cors(database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        response = client.get("/api/health", headers={"Origin": "http://127.0.0.1:5173"})
        assert response.status_code == 200
        assert response.json()["database"] == "ready"
        assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
        denied = client.get("/api/health", headers={"Origin": "https://untrusted.example"})
        assert "access-control-allow-origin" not in denied.headers
        assert client.get("/api/health/live").json() == {"status": "ok"}
        docs = client.get("/docs")
        assert docs.status_code == 200 and "OpenAPI schema" in docs.text
        assert "<script" not in docs.text and "https://" not in docs.text
        assert client.get("/api/health", headers={"Host": "untrusted.example"}).status_code == 400


def test_unmigrated_database_is_not_ready(tmp_path: Path) -> None:
    with TestClient(
        create_app(Settings(database_url=f"sqlite:///{tmp_path / 'unmigrated.db'}"))
    ) as client:
        assert client.get("/api/health/live").status_code == 200
        response = client.get("/api/health")
        assert response.status_code == 503
        assert response.json()["database"] == "unavailable"


def test_migration_and_identity_persistence(database_url: str) -> None:
    engine = build_engine(database_url)
    identifier = uuid4()
    with Session(engine) as session:
        session.add(
            User(id=identifier, user_id=identifier, display_name="Local user", mode="local")
        )
        session.commit()
    with Session(engine) as session:
        user = session.get(User, identifier)
        assert user is not None and user.display_name == "Local user"
    engine.dispose()
    command.check(Config("alembic.ini"))
    command.downgrade(Config("alembic.ini"), "base")
    engine = build_engine(database_url)
    assert "users" not in inspect(engine).get_table_names()
    engine.dispose()
    command.upgrade(Config("alembic.ini"), "head")


def test_settings_validation() -> None:
    with pytest.raises(ValueError):
        Settings(database_url="mysql://localhost/app")
    with pytest.raises(ValueError):
        Settings(api_port=0)
