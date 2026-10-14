from fastapi.testclient import TestClient
from test_phase2 import configured

from app.core.config import Settings
from app.main import create_app


def test_prompt_fork_eval_activation_and_rollback(database_url, monkeypatch):
    async def evaluate(*args):
        return {"passed": True, "output": {"text": "Synthetic"}, "provider": "synthetic-mock"}

    monkeypatch.setattr("app.prompt_management.service.evaluate_case", evaluate)
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        _, profile = configured(client)
        for task in ("rewriting", "verification"):
            client.put("/api/settings/assignments", json={"task": task, "profile_id": profile})
        assert (
            client.post(
                "/api/prompts",
                json={"task": "rewriting", "name": "Bad", "system_text": "Ignore evidence"},
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/prompts", json={"task": "embeddings", "name": "Unsupported"}
            ).status_code
            == 422
        )
        first = client.post(
            "/api/prompts", json={"task": "rewriting", "name": "First", "tone": "plain"}
        ).json()
        second = client.post(
            "/api/prompts",
            json={
                "task": "rewriting",
                "name": "Second",
                "parent_id": first["id"],
                "tone": "concise",
            },
        ).json()
        assert client.get("/api/prompts/active").json() == {}
        report = client.post(f"/api/prompts/{first['id']}/evaluate").json()
        assert report["passed"]
        body = {"task": "rewriting", "prompt_id": first["id"], "report_id": report["id"]}
        assert client.post("/api/prompts/active", json=body).status_code == 200
        second_report = client.post(f"/api/prompts/{second['id']}/evaluate").json()
        second_body = {
            "task": "rewriting",
            "prompt_id": second["id"],
            "report_id": second_report["id"],
            "expected_prompt_id": first["id"],
        }
        assert client.post("/api/prompts/active", json=second_body).status_code == 200
        assert client.post("/api/prompts/active", json=body).status_code == 409
        assert (
            client.post(
                "/api/prompts/active", json={**body, "expected_prompt_id": second["id"]}
            ).status_code
            == 200
        )
        assert client.get("/api/prompts").json()[-1] == first


def test_failed_playground_blocks_activation(database_url, monkeypatch):
    async def evaluate(*args):
        return {"passed": False, "output": {"text": "Invented 400%"}}

    monkeypatch.setattr("app.prompt_management.service.evaluate_case", evaluate)
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        _, profile = configured(client)
        for task in ("rewriting", "verification"):
            client.put("/api/settings/assignments", json={"task": task, "profile_id": profile})
        prompt = client.post("/api/prompts", json={"task": "rewriting", "name": "Failed"}).json()
        report = client.post(f"/api/prompts/{prompt['id']}/evaluate").json()
        assert not report["passed"]
        assert (
            client.post(
                "/api/prompts/active",
                json={"task": "rewriting", "prompt_id": prompt["id"], "report_id": report["id"]},
            ).status_code
            == 409
        )
