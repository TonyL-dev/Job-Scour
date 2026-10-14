"""Offline conversion of existing protected fields. Stop the backend first.

Keep APP_ENCRYPTION_KEY outside the database and backups. Conversion is one transaction.
SQLite VACUUM removes old freed pages from the live file; pre-existing backups remain plaintext.
"""

from sqlalchemy import MetaData, Table, select, update

from app.core.config import get_settings
from app.core.database import Base, build_engine
from app.core.encryption import PREFIX, SecureIndex, SecureJSON, SecureText, decrypt, encrypt, key
from app.main import create_app  # noqa: F401 -- registers domain models


def main() -> None:
    if key() is None:
        raise SystemExit("Set APP_ENCRYPTION_KEY to base64 of 32 random bytes before conversion")
    engine = build_engine(get_settings().database_url)
    with engine.begin() as conn:
        for model_table in Base.metadata.sorted_tables:
            columns = [
                c
                for c in model_table.c
                if isinstance(c.type, (SecureJSON, SecureText, SecureIndex))
            ]
            if not columns:
                continue
            table = Table(model_table.name, MetaData(), autoload_with=conn)
            for row in conn.execute(select(table)).mappings():
                values = {}
                for col in columns:
                    value = row[col.name]
                    if value is None:
                        continue
                    if isinstance(col.type, SecureIndex):
                        if not value.startswith("stonks:hmac:1:"):
                            values[col.name] = col.type.process_bind_param(value, conn.dialect)
                    elif isinstance(col.type, SecureText):
                        if value.startswith(PREFIX):
                            decrypt(value, col.type.context)  # verify the key before commit
                        else:
                            values[col.name] = encrypt(value, col.type.context)
                    elif (
                        isinstance(col.type, SecureJSON)
                        and isinstance(value, dict)
                        and "$stonks_ciphertext" in value
                    ):
                        decrypt(value["$stonks_ciphertext"], col.type.context)
                    elif isinstance(col.type, SecureJSON):
                        values[col.name] = col.type.process_bind_param(value, conn.dialect)
                if values:
                    conn.execute(update(table).where(table.c.id == row["id"]).values(**values))
    if engine.dialect.name == "sqlite":
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.exec_driver_sql("VACUUM")
    engine.dispose()
    print(
        "Protected fields encrypted. Preserve the key separately; "
        "existing exports/backups are not changed."
    )


if __name__ == "__main__":
    main()
