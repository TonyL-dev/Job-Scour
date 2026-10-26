"""Optional authenticated field encryption; keys live only in the backend environment."""

import base64
import hashlib
import hmac
import json
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import JSON, Text
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

PREFIX = "stonks:aesgcm:1:"


def key() -> bytes | None:
    value = os.environ.get("APP_ENCRYPTION_KEY")
    if not value:
        return None
    try:
        result = base64.b64decode(value, validate=True)
    except ValueError as error:
        raise RuntimeError("APP_ENCRYPTION_KEY must be base64 encoded") from error
    if len(result) != 32:
        raise RuntimeError("APP_ENCRYPTION_KEY must encode 32 random bytes")
    return result


def encrypt(value: str, context: str) -> str:
    secret = key()
    if secret is None:
        return value
    nonce = os.urandom(12)
    return (
        PREFIX
        + base64.b64encode(
            nonce + AESGCM(secret).encrypt(nonce, value.encode(), context.encode())
        ).decode()
    )


def decrypt(value: str, context: str) -> str:
    secret = key()
    if not value.startswith(PREFIX):
        if secret:
            # Enabling a key requires offline conversion of existing fields; silently
            # accepting plaintext here would conceal an incomplete conversion.
            raise RuntimeError(
                "Plaintext protected field: run python -m app.privacy.encrypt_store "
                "with the backend stopped"
            )
        return value
    if secret is None:
        raise RuntimeError("Encrypted data requires APP_ENCRYPTION_KEY")
    raw = base64.b64decode(value[len(PREFIX) :], validate=True)
    return AESGCM(secret).decrypt(raw[:12], raw[12:], context.encode()).decode()


class SecureText(TypeDecorator[str]):
    impl = Text
    cache_ok = True

    def __init__(self, context: str) -> None:
        super().__init__()
        self.context = context

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        return encrypt(value, self.context) if value is not None else None

    def process_result_value(self, value: str | None, dialect: Dialect) -> str | None:
        return decrypt(value, self.context) if value is not None else None


class SecureJSON(TypeDecorator[Any]):
    impl = JSON
    cache_ok = True

    def __init__(self, context: str) -> None:
        super().__init__()
        self.context = context

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        if value is None or key() is None:
            return value
        return {"$stonks_ciphertext": encrypt(json.dumps(value, ensure_ascii=False), self.context)}

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:
        if value is None:
            return None
        if isinstance(value, dict) and "$stonks_ciphertext" in value:
            return json.loads(decrypt(value["$stonks_ciphertext"], self.context))
        if key():
            raise RuntimeError(
                "Plaintext protected JSON: run python -m app.privacy.encrypt_store "
                "with the backend stopped"
            )
        return value


class SecureIndex(TypeDecorator[str]):
    """A blind equality index; original display values are encrypted separately."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        secret = key()
        if value is None or secret is None:
            return value
        return (
            "stonks:hmac:1:"
            + hmac.new(
                secret, b"skills.normalized_name:" + value.encode(), hashlib.sha256
            ).hexdigest()
        )
