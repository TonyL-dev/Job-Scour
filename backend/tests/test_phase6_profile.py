import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from fastapi.testclient import TestClient
from test_phase2 import configured

from app.core.config import Settings
from app.main import create_app
from app.profile.schemas import Questions


def test_profile_user_confirmation_and_stale_source(database_url, monkeypatch):
    async def questions(*args):
        return Questions(questions=["What outcome did you observe?", "How did you measure it?"])

    monkeypatch.setattr("app.profile.service.profile_questions", questions)
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        _, profile = configured(client)
        client.put(
            "/api/settings/assignments", json={"task": "profile_questions", "profile_id": profile}
        )
        source = client.post(
            "/api/career",
            json={"type": "project", "name": "Orbit", "description": "Built Python APIs"},
        ).json()
        review = client.post("/api/profile", json={"kind": "project", "record_id": source["id"]})
        assert review.status_code == 201, review.text
        identifier = review.json()["id"]
        assert (
            client.get(f"/api/career/project/{source['id']}").json()["data"]["description"]
            == "Built Python APIs"
        )
        proposed = client.put(
            f"/api/profile/{identifier}/answers",
            json={"expected_revision": 1, "answers": ["Reduced latency by 40%", "unknown"]},
        ).json()
        assert proposed["proposed"]["description"] == "Built Python APIs\nReduced latency by 40%"
        commit = client.post(
            f"/api/profile/{identifier}/confirm",
            json={"expected_revision": 2, "data": proposed["proposed"]},
        )
        assert commit.status_code == 200, commit.text
        assert commit.json()["status"] == "confirmed"
        assert (
            client.post(
                f"/api/profile/{identifier}/confirm",
                json={"expected_revision": 2, "data": proposed["proposed"]},
            ).json()
            == commit.json()
        )
        fresh = client.post(
            "/api/profile", json={"kind": "project", "record_id": source["id"]}
        ).json()
        client.put(
            f"/api/career/{source['id']}",
            json={"type": "project", "name": "Orbit", "description": "Changed source"},
        )
        stale = client.put(
            f"/api/profile/{fresh['id']}/answers",
            json={"expected_revision": 1, "answers": ["Invented outcome", "skip"]},
        )
        assert stale.status_code == 409
        assert (
            client.get(f"/api/career/project/{source['id']}").json()["data"]["description"]
            == "Changed source"
        )


@pytest.mark.parametrize("action", ["cancel", "retire", "lock", "delete"])
def test_pending_profile_questions_cannot_save_after_revocation(database_url, monkeypatch, action):
    started, released = Event(), Event()

    async def held_questions(*args):
        started.set()
        while not released.is_set():
            await asyncio.sleep(0.01)
        return Questions(questions=["What outcome did you observe?"])

    monkeypatch.setattr("app.profile.service.profile_questions", held_questions)
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        _, profile = configured(client)
        client.put(
            "/api/settings/assignments", json={"task": "profile_questions", "profile_id": profile}
        )
        source = client.post(
            "/api/career",
            json={"type": "project", "name": "Orbit", "description": "Original user facts"},
        ).json()
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(
                client.post, "/api/profile", json={"kind": "project", "record_id": source["id"]}
            )
            assert started.wait(10)
            if action == "cancel":
                response = client.post(f"/api/profile/{source['id']}/cancel")
            elif action == "retire":
                response = client.delete(f"/api/career/project/{source['id']}")
            elif action == "lock":
                response = client.post("/api/privacy/lock")
            else:
                response = client.post(
                    "/api/privacy/delete-all", json={"confirmation": "DELETE ALL MY DATA"}
                )
            assert response.status_code in {200, 204}
            released.set()
            assert pending.result(timeout=10).status_code in {404, 409, 423}
        assert client.get("/api/profile").json() == []
        if action == "cancel":
            assert (
                client.get(f"/api/career/project/{source['id']}").json()["data"]["description"]
                == "Original user facts"
            )


def test_profile_refusal_and_unsupported_model_numbers_create_no_facts(database_url, monkeypatch):
    async def questions(*args):
        return Questions(questions=["Did latency improve by 400%?"])

    monkeypatch.setattr("app.profile.service.profile_questions", questions)
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        _, profile = configured(client)
        client.put(
            "/api/settings/assignments", json={"task": "profile_questions", "profile_id": profile}
        )
        source = client.post(
            "/api/career", json={"type": "project", "name": "Orbit", "description": "Original"}
        ).json()
        body = {"kind": "project", "record_id": source["id"]}
        assert client.post("/api/profile", json=body).status_code == 502
        assert client.get("/api/profile").json() == []

        async def safe_questions(*args):
            return Questions(questions=["What outcome did you observe?"])

        monkeypatch.setattr("app.profile.service.profile_questions", safe_questions)
        review = client.post("/api/profile", json=body).json()
        answered = client.put(
            f"/api/profile/{review['id']}/answers",
            json={"expected_revision": 1, "answers": ["unknown"]},
        ).json()
        assert answered["proposed"]["description"] == "Original"
        assert client.post(f"/api/profile/{review['id']}/discard?revision=2").status_code == 200
        assert (
            client.get(f"/api/career/project/{source['id']}").json()["data"]["description"]
            == "Original"
        )
