import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import Request
from sqlalchemy import DateTime, Engine, ForeignKey, Uuid, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


class OwnedRecord:
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


def build_engine(url: str) -> Engine:
    passphrase = os.environ.get("APP_DATABASE_PASSPHRASE")
    if passphrase:
        if (
            not url.startswith("sqlite")
            or not make_url(url).database
            or make_url(url).database == ":memory:"
        ):
            raise RuntimeError(
                "Database passphrase encryption requires a file-backed local SQLite database"
            )
        from app.core.cipher_database import cipher, connection, engine_key

        path = Path(str(make_url(url).database)).resolve()
        derived = engine_key(path, passphrase)
        return create_engine(
            url,
            module=cipher,
            creator=lambda: connection(path, derived),
            pool_pre_ping=True,
            hide_parameters=True,
        )
    kwargs = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=kwargs, pool_pre_ping=True, hide_parameters=True)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection: object, _record: object) -> None:
            # SQLAlchemy passes the SQLite DBAPI connection here.
            from sqlite3 import Connection

            assert isinstance(connection, Connection)
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA secure_delete=ON")

    return engine


def get_session(request: Request) -> Iterator[Session]:
    from app.core.workspace import bind

    with Session(request.app.state.engine) as session:
        bind(session, request.app.state.barrier)
        yield session
