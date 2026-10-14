import asyncio
from io import BytesIO
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.ai.gateway import Gateway
from app.core.config import Settings
from app.core.http import MAX_BODY_BYTES
from app.main import create_app
from app.privacy.service import LockState
from app.rendering import service as rendering
from app.resumes.schemas import ResumeDocument


def document() -> ResumeDocument:
    return ResumeDocument.model_validate(
        {
            "schema_version": 1,
            "header": {"name": "Synthetic Cache Example"},
            "sections": [],
            "metadata": {"template_id": str(rendering.TEMPLATES[0].id)},
        }
    )


def test_pdf_cache_parity_expiry_bounds_and_invalidation(monkeypatch: pytest.MonkeyPatch) -> None:
    rendering.clear_cache()
    original = rendering.print_artifact
    with patch.object(rendering, "print_artifact", wraps=original) as printer:
        first = rendering.render(document())
        second = rendering.render(document())
        assert first == second
        assert printer.call_count == 1
        assert "Synthetic Cache Example" in PdfReader(BytesIO(second.pdf)).pages[0].extract_text()
        with rendering.CACHE_LOCK:
            rendering.CACHE[first.html_hash] = (0, first)
        rendering.render(document())
        assert printer.call_count == 2
        rendering.clear_cache()
        rendering.render(document())
        assert printer.call_count == 3
    # Count and byte caps are independent of PDF length or data sensitivity.
    for index in range(10):
        rendering.retain(str(index), first, rendering.cache_epoch)
    assert len(rendering.CACHE) <= 8
    monkeypatch.setattr(rendering, "CACHE_BYTES", 1)
    rendering.clear_cache()
    rendering.retain("large", first, rendering.cache_epoch)
    assert not rendering.CACHE


def test_late_render_cannot_repopulate_revoked_cache() -> None:
    rendering.clear_cache()
    original = rendering.print_artifact

    def revoked(artifact: str, digest: str) -> rendering.Rendered:
        result = original(artifact, digest)
        rendering.clear_cache()
        return result

    with patch.object(rendering, "print_artifact", side_effect=revoked):
        rendering.render(document())
    assert not rendering.CACHE


def test_lock_delete_passcode_and_expiry_clear_cache(database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        result = rendering.render(document())
        assert rendering.CACHE
        assert client.post("/api/privacy/passcode", json={"passcode": "synthetic123"}).is_success
        assert not rendering.CACHE
        rendering.retain("private", result, rendering.cache_epoch)
        assert client.post("/api/privacy/lock").is_success
        assert not rendering.CACHE
        assert client.post("/api/privacy/unlock", json={"passcode": "synthetic123"}).is_success
        rendering.retain("private", result, rendering.cache_epoch)
        assert (
            client.post(
                "/api/privacy/delete-all",
                json={
                    "confirmation": "DELETE ALL MY DATA",
                },
            ).status_code
            == 204
        )
        assert not rendering.CACHE
        rendering.retain("private", result, rendering.cache_epoch)
        state = LockState("enabled")
        state.sessions["expired"] = 0
        assert not state.unlocked("expired")
        assert not rendering.CACHE


def test_body_limit_for_declared_and_chunked_writes_and_error_headers(database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        for response in (
            client.post(
                "/api/career",
                content=b"x",
                headers={
                    "Content-Length": str(MAX_BODY_BYTES + 1),
                },
            ),
            client.post("/api/career", content=iter([b"x" * MAX_BODY_BYTES, b"x"])),
        ):
            assert response.status_code == 413
            assert response.headers["Cache-Control"] == "no-store"
            assert response.headers["X-Content-Type-Options"] == "nosniff"
            assert response.headers["X-Frame-Options"] == "DENY"
        response = client.post("/api/career", json={})
        assert response.status_code == 422
        assert response.headers["Referrer-Policy"] == "no-referrer"
        response = client.post("/api/career", json={}, headers={"Origin": "https://evil.test"})
        assert response.status_code == 403
        assert response.headers["Cache-Control"] == "no-store"


def test_ai_queue_bounds_and_cancellation_release() -> None:
    async def scenario() -> None:
        gateway = Gateway()
        release = asyncio.Event()
        entered = asyncio.Event()

        async def held() -> None:
            async with gateway.slot():
                entered.set()
                await release.wait()

        active = asyncio.create_task(held())
        await entered.wait()
        waiters = [asyncio.create_task(held()) for _ in range(4)]
        await asyncio.sleep(0)
        assert gateway.pending == 5
        with pytest.raises(HTTPException) as error:
            async with gateway.slot():
                pass
        assert error.value.status_code == 429
        for waiter in waiters:
            waiter.cancel()
        await asyncio.gather(*waiters, return_exceptions=True)
        assert gateway.pending == 1
        active.cancel()
        await asyncio.gather(active, return_exceptions=True)
        assert gateway.pending == 0
        async with gateway.slot():
            assert gateway.pending == 1
        assert gateway.pending == 0

    asyncio.run(scenario())
