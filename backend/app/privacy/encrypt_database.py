"""Offline, non-destructive SQLite -> SQLCipher copy. Never overwrites the source.

Set APP_DATABASE_PASSPHRASE and run python -m app.privacy.encrypt_database --output PATH.
After verifying the copy, point APP_DATABASE_URL at PATH. Keep PATH.salt with backups.
"""

import argparse
import os
from pathlib import Path

from sqlalchemy.engine import make_url

from app.core.cipher_database import cipher, create_salt, derive, salt_path
from app.core.config import get_settings


def convert(source: Path, target: Path, passphrase: str) -> None:
    source = source.resolve(strict=True)
    target = target.resolve()
    if source == target or target.exists() or salt_path(target).exists():
        raise RuntimeError(
            "Choose a new output file; source and existing files are never overwritten"
        )
    with source.open("rb") as input_file:
        header = input_file.read(16)
    if header != b"SQLite format 3\x00":
        raise RuntimeError("Source must be a plaintext SQLite database")
    # Reserve the target before creating its salt; remove only this operation's failed copy.
    target.touch(exist_ok=False)
    conn = None
    success = False
    try:
        derived = derive(passphrase, create_salt(target))
        conn = cipher.connect(str(source))
        conn.execute("ATTACH DATABASE ? AS encrypted KEY ?", (str(target), "x'" + derived + "'"))
        conn.execute("SELECT sqlcipher_export('encrypted')").fetchone()
        conn.execute("DETACH DATABASE encrypted")
        conn.close()
        conn = None
        from app.core.cipher_database import connection

        checked = connection(target, derived)
        try:
            if checked.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise RuntimeError("Encrypted copy failed integrity check")
            if checked.execute("PRAGMA foreign_key_check").fetchall():
                raise RuntimeError("Encrypted copy failed foreign-key check")
        finally:
            checked.close()
        success = True
    finally:
        if conn:
            conn.close()
        if not success:
            target.unlink(missing_ok=True)
            salt_path(target).unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    url = make_url(get_settings().database_url)
    passphrase = os.environ.get("APP_DATABASE_PASSPHRASE")
    if url.drivername != "sqlite" or not url.database or not passphrase:
        raise SystemExit("Set a plaintext SQLite APP_DATABASE_URL and APP_DATABASE_PASSPHRASE")
    convert(Path(url.database), args.output, passphrase)
    print("Verified encrypted copy created. Change APP_DATABASE_URL to its path.")
    print("Original plaintext database remains intact; handle it and earlier backups privately.")


if __name__ == "__main__":
    main()
