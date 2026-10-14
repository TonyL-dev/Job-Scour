"""Mandatory private asset encryption, independent of optional database encryption."""

import base64
import os
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException


def key() -> bytes:
    raw = os.environ.get("APP_UPLOAD_KEY") or os.environ.get("APP_ENCRYPTION_KEY")
    try:
        result = base64.b64decode(raw or "", validate=True)
        if len(result) != 32:
            raise ValueError()
        return result
    except ValueError as error:
        raise HTTPException(
            503, "Private file storage requires APP_UPLOAD_KEY (base64 of 32 random bytes)"
        ) from error


def encrypt(content: bytes, owner: UUID, identifier: UUID) -> str:
    nonce = os.urandom(12)
    return base64.b64encode(
        nonce
        + AESGCM(key()).encrypt(nonce, content, f"stonks.asset.v1:{owner}:{identifier}".encode())
    ).decode()


def decrypt(content: str, owner: UUID, identifier: UUID) -> bytes:
    try:
        raw = base64.b64decode(content, validate=True)
        return AESGCM(key()).decrypt(
            raw[:12], raw[12:], f"stonks.asset.v1:{owner}:{identifier}".encode()
        )
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(503, "Private asset key is wrong or content is corrupt") from error
