from uuid import UUID

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_phase2 import ANALYSIS, TEXT, configured, sse

from app.ai.gateway import Gateway
from app.career.models import Skill
from app.core.config import Settings
from app.core.database import build_engine, utc_now
from app.jobs.models import MatchRecord
from app.main import create_app


def test_career_retirement_during_embedding_refuses_a_stale_match(database_url: str) -> None:
    engine = build_engine(database_url)
    retired = False
    skill_id: UUID

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal retired
        if request.url.path.endswith("/embeddings"):
            if not retired:
                with Session(engine) as db:
                    row = db.get(Skill, skill_id)
                    assert row is not None
                    row.deleted_at = utc_now()
                    db.commit()
                retired = True
            return httpx.Response(200, json={"data": [{"embedding": [1.0, 0.5]}]})
        return sse(ANALYSIS)

    with TestClient(create_app(Settings(database_url=database_url))) as client:
        client.app.state.gateway = Gateway(httpx.MockTransport(handle))
        _endpoint, profile = configured(client)
        client.put("/api/settings/assignments", json={"task": "embeddings", "profile_id": profile})
        skill_id = UUID(
            client.post(
                "/api/career", json={"type": "skill", "name": "Python", "category": "language"}
            ).json()["id"]
        )
        job = client.post("/api/jobs", json={"raw_text": TEXT}).json()
        response = client.post(f"/api/jobs/{job['id']}/analyze", json={"use_embeddings": True})
        assert response.status_code == 409
        assert "Career library changed" in response.json()["detail"]
        retry = client.post(f"/api/jobs/{job['id']}/analyze", json={})
        assert retry.status_code == 200 and retry.json()["cached"] is True
        assert retry.json()["match"]["items"] == []
        with Session(engine) as db:
            assert len(list(db.scalars(select(MatchRecord)))) == 1
    engine.dispose()
