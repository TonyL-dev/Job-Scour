import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.ai import codex
from app.ai.gateway import Gateway
from app.core.config import Settings
from app.main import create_app
from app.settings.schemas import ConnectionResult, Endpoint, EndpointInput, Profile


def test_codex_consent_and_assignment(database_url: str) -> None:
    data = {"name": "Codex", "provider": "codex", "base_url": "https://chatgpt.com/codex"}
    with pytest.raises(ValidationError):
        EndpointInput.model_validate(data)
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        endpoint = client.post("/api/settings/endpoints", json={**data, "remote_consent": True})
        assert endpoint.status_code == 201
        body = {"endpoint_id": endpoint.json()["id"], "model": "default"}
        assert (
            client.post(
                "/api/settings/profiles", json={**body, "structured_mode": "none"}
            ).status_code
            == 422
        )
        profile = client.post("/api/settings/profiles", json=body).json()
        assignment = {"profile_id": profile["id"], "task": "embeddings"}
        assert client.put("/api/settings/assignments", json=assignment).status_code == 422
        assignment["task"] = "job_analysis"
        assert client.put("/api/settings/assignments", json=assignment).status_code == 200


def test_codex_adapter_isolated_and_tool_output_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PRIVATE_KEY", "must-not-leave")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-use")
    assert "LLM_PRIVATE_KEY" not in codex.environment()
    assert "OPENAI_API_KEY" not in codex.environment()
    tool_event = False

    async def fake_ready() -> None:
        pass

    async def fake_run(args: list[str], cwd: str, prompt: str = "", timeout: float = 240) -> bytes:
        assert "--ignore-user-config" in args and "--ephemeral" in args
        assert args[args.index("--sandbox") + 1] == "read-only"
        assert "features.shell_tool=false" in args and 'web_search="disabled"' in args
        assert "features.apps=false" in args and "features.plugins=false" in args
        assert "--model" not in args
        assert Path(cwd).resolve() != Path.cwd().resolve()
        assert "supplied source" in prompt and "Do not use tools" in prompt
        schema = json.loads(
            Path(args[args.index("--output-schema") + 1]).read_text(encoding="utf-8")
        )
        assert schema["additionalProperties"] is False
        Path(args[args.index("--output-last-message") + 1]).write_text(
            '{"ok":true}', encoding="utf-8"
        )
        return b'{"item":{"type":"command_execution"}}' if tool_event else b""

    monkeypatch.setattr(codex, "ready", fake_ready)
    monkeypatch.setattr(codex, "run", fake_run)
    assert (
        asyncio.run(
            codex.structured(
                "default", "system", "supplied source", ConnectionResult.model_json_schema()
            )
        )
        == '{"ok":true}'
    )
    tool_event = True
    with pytest.raises(HTTPException, match="tool call"):
        asyncio.run(
            codex.structured(
                "default", "system", "supplied source", ConnectionResult.model_json_schema()
            )
        )


def test_codex_gateway_blocks_stale_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake(*args: object) -> str:
        return '{"ok":true}'

    monkeypatch.setattr(codex, "structured", fake)
    endpoint = Endpoint(
        id=uuid4(),
        name="Codex",
        provider="codex",
        base_url="https://chatgpt.com/codex",
        remote_consent=True,
    )
    profile = Profile(id=uuid4(), endpoint_id=endpoint.id, model="default")
    gateway = Gateway()
    assert asyncio.run(gateway.test(endpoint, profile)).ok
    gateway.configure(endpoint.model_copy(update={"enabled": False, "remote_consent": False}))
    with pytest.raises(HTTPException, match="settings changed"):
        asyncio.run(gateway.test(endpoint, profile))


def test_codex_process_timeout_and_cancellation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("STONKS_CODEX_CLI", sys.executable)
    pid_path = tmp_path / "pid"
    script = (
        "import os,time,pathlib; pathlib.Path("
        + repr(str(pid_path))
        + ").write_text(str(os.getpid())); time.sleep(30)"
    )

    async def cancel() -> None:
        task = asyncio.create_task(codex.run(["-c", script], str(tmp_path)))
        for _ in range(100):
            if pid_path.exists():
                break
            await asyncio.sleep(0.02)
        assert pid_path.exists()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancel())
    with pytest.raises(HTTPException, match="timed out"):
        asyncio.run(codex.run(["-c", "import time; time.sleep(30)"], str(tmp_path), timeout=0.1))
    if os.name != "nt":
        with pytest.raises(ProcessLookupError):
            os.kill(int(pid_path.read_text()), 0)
