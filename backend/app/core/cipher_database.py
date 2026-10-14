"""SQLCipher full SQLite encryption with an Argon2id-derived passphrase key."""

import os
from pathlib import Path
from typing import Any

import sqlcipher3.dbapi2 as cipher
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id


def derive(passphrase: str, salt: bytes) -> str:
    if len(passphrase) < 8:
        raise RuntimeError("Database passphrase must contain at least eight characters")
    return (
        Argon2id(salt=salt, length=32, iterations=3, lanes=4, memory_cost=65536)
        .derive(passphrase.encode())
        .hex()
    )


def salt_path(path: Path) -> Path:
    return Path(str(path) + ".salt")


def create_salt(path: Path) -> bytes:
    salt = os.urandom(16)
    with salt_path(path).open("xb") as stream:
        stream.write(salt)
        stream.flush()
        os.fsync(stream.fileno())
    return salt


def connection(path: Path, derived: str) -> Any:
    conn = cipher.connect(str(path), check_same_thread=False)
    try:
        conn.execute(f"PRAGMA key = \"x'{derived}'\"")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA secure_delete = ON")
        conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
    except Exception:
        conn.close()
        raise RuntimeError(
            "Cannot unlock encrypted SQLite database. Check passphrase and salt."
        ) from None
    return conn


def engine_key(path: Path, passphrase: str) -> str:
    location = salt_path(path)
    if not location.exists():
        if path.exists() and path.stat().st_size:
            raise RuntimeError(
                "Existing database requires offline SQLCipher conversion to a new file"
            )
        try:
            salt = create_salt(path)
        except FileExistsError:
            salt = location.read_bytes()
    else:
        salt = location.read_bytes()
    if len(salt) != 16:
        raise RuntimeError("Invalid SQLCipher salt file")
    return derive(passphrase, salt)


__all__ = ["cipher", "derive", "salt_path", "create_salt", "connection", "engine_key"]
