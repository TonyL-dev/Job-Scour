import base64
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, inspect, select, update
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import Base
from app.core.encryption import SecureJSON, SecureText


def passcode(db: Session, owner: UUID) -> str | None:
    if not inspect(db.get_bind()).has_table("users"):
        return None
    return db.scalar(select(User.password_hash).where(User.id == owner, User.user_id == owner))


def set_passcode(db: Session, owner: UUID, value: str) -> None:
    db.execute(
        update(User).where(User.id == owner, User.user_id == owner).values(password_hash=value)
    )
    db.commit()


def export(db: Session, owner: UUID) -> dict[str, object]:
    result: dict[str, object] = {"format": "stonks.export.v1", "tables": {}}
    tables: dict[str, object] = {}
    for table in Base.metadata.sorted_tables:
        if table.name == "users":
            continue
        if "user_id" in table.c:
            tables[table.name] = jsonable_encoder(
                [
                    {
                        k: {
                            "encoding": "base64",
                            "encrypted": True,
                            "value": base64.b64encode(v).decode(),
                        }
                        if isinstance(v, bytes)
                        else v
                        for k, v in dict(r).items()
                    }
                    for r in db.execute(select(table).where(table.c.user_id == owner)).mappings()
                ]
            )
    result["tables"] = tables
    return result


def delete_all(db: Session, owner: UUID) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        if table.name != "users" and "user_id" in table.c:
            db.execute(delete(table).where(table.c.user_id == owner))
    db.commit()


def verify_store(db: Session) -> None:
    # doctor/offline commands do not import every router. Register protected file tables
    # explicitly before inspecting metadata, including in a newly installed environment.
    from app.core.model_registry import register_models

    register_models()

    existing = set(inspect(db.get_bind()).get_table_names())
    for table in Base.metadata.sorted_tables:
        protected = [c for c in table.c if isinstance(c.type, (SecureJSON, SecureText))]
        if table.name in existing and protected:
            # Decode through mapped types, failing before any requests if keys or conversion
            # are missing. No sensitive values are logged or returned.
            for _row in db.execute(select(*protected)):
                pass
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    from app.core import private_files

    if "template_assets" in existing:
        table = Base.metadata.tables["template_assets"]
        for asset in db.execute(select(table.c.user_id, table.c.id, table.c.ciphertext)):
            private_files.decrypt(asset.ciphertext, asset.user_id, asset.id)
    if "import_runs" in existing:
        table = Base.metadata.tables["import_runs"]
        for upload in db.execute(
            select(table.c.user_id, table.c.original).where(table.c.original.is_not(None))
        ):
            encrypted = upload.original
            try:
                AESGCM(private_files.key()).decrypt(
                    encrypted[:12],
                    encrypted[12:],
                    b"stonks.upload.v1:" + str(upload.user_id).encode(),
                )
            except Exception as error:
                raise RuntimeError(
                    "Retained upload key missing/wrong or ciphertext corrupt"
                ) from error
