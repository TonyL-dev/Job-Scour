import asyncio
import json
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.evaluation import assess, fixtures
from app.ai.gateway import Gateway
from app.ai.models import Embedding
from app.ai.prompts import validate_evidence
from app.ai.retrieval import ALIASES, contains
from app.ai.service import explicit_metadata
from app.auth.models import User
from app.core.config import Settings
from app.core.database import build_engine
from app.jobs.models import AnalysisRecord
from app.jobs.schemas import JobAnalysis
from app.main import create_app
from app.settings.models import ModelProfile
from app.settings.schemas import ConnectionResult, Endpoint, Profile

TEXT = "Required: Python and Kubernetes. Preferred: SQL. Build APIs."
ANALYSIS = {
    "required_skills": [
        {"term": "Python", "evidence": "Python"},
        {"term": "Kubernetes", "evidence": "Kubernetes"},
    ],
    "preferred_skills": [{"term": "SQL", "evidence": "SQL"}],
    "technologies": [],
    "responsibilities": [{"term": "Build APIs", "evidence": "Build APIs"}],
    "company_values": [],
    "industry_terms": [],
    "keywords": [
        {"term": "Python", "evidence": "Python", "weight": 5},
        {"term": "Kubernetes", "evidence": "Kubernetes", "weight": 5},
        {"term": "SQL", "evidence": "SQL", "weight": 2},
    ],
    "seniority": None,
    "years_experience": None,
}


def sse(result: object) -> httpx.Response:
    content = json.dumps(result)
    # Multiple content chunks prove incremental assembly.
    chunks = [content[: len(content) // 2], content[len(content) // 2 :]]
    data = "".join(
        "data: " + json.dumps({"choices": [{"delta": {"content": c}}]}) + "\n\n" for c in chunks
    )
    return httpx.Response(
        200, text=data + "data: [DONE]\n\n", headers={"Content-Type": "text/event-stream"}
    )


def configured(client: TestClient) -> tuple[str, str]:
    endpoint = client.post(
        "/api/settings/endpoints",
        json={"name": "Local", "provider": "lm_studio", "base_url": "http://localhost:1234/v1"},
    ).json()
    assert endpoint["base_url"] == "http://127.0.0.1:1234/v1"
    profile = client.post(
        "/api/settings/profiles", json={"endpoint_id": endpoint["id"], "model": "test-model"}
    ).json()
    assert (
        client.put(
            "/api/settings/assignments", json={"task": "job_analysis", "profile_id": profile["id"]}
        ).status_code
        == 200
    )
    return endpoint["id"], profile["id"]


def test_settings_privacy_isolation_and_gateway_boundary(database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        endpoint, profile = configured(client)
        assert (
            client.post(
                "/api/settings/endpoints",
                json={
                    "name": "Bad",
                    "provider": "openai_compatible",
                    "base_url": "https://remote.example/v1",
                },
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/settings/endpoints",
                json={
                    "name": "Bad",
                    "provider": "lm_studio",
                    "base_url": "http://localhost.evil/v1",
                },
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/settings/endpoints",
                json={
                    "name": "Bad",
                    "provider": "lm_studio",
                    "base_url": "http://secret@127.0.0.1/v1",
                },
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/settings/profiles", json={"endpoint_id": str(uuid4()), "model": "test"}
            ).status_code
            == 404
        )
        assert (
            client.post(
                "/api/settings/endpoints",
                json={
                    "name": "Local",
                    "provider": "lm_studio",
                    "base_url": "http://localhost:1234",
                },
                headers={"Origin": "https://evil.example"},
            ).status_code
            == 403
        )
        disabled = client.put(
            "/api/settings/endpoints/" + endpoint,
            json={
                "name": "Local",
                "provider": "lm_studio",
                "base_url": "http://127.0.0.1:1234/v1",
                "enabled": False,
            },
        ).json()
        assert disabled["enabled"] is False
        client.app.state.gateway = Gateway(
            httpx.MockTransport(lambda r: pytest.fail("Disabled endpoint made an outbound call"))
        )
        assert client.post(f"/api/settings/profiles/{profile}/test").status_code == 409
        engine = build_engine(database_url)
        other = uuid4()
        with Session(engine) as db:
            db.add(User(id=other, user_id=other, display_name="Other", mode="server"))
            db.commit()
            db.add(
                ModelProfile(
                    user_id=other,
                    endpoint_id=UUID(endpoint),
                    model="bad",
                    context_window=4096,
                    max_output_tokens=100,
                    temperature=0,
                    top_p=1,
                    structured_mode="none",
                )
            )
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
        engine.dispose()
    with TestClient(create_app(Settings(database_url=database_url, mode="server"))) as client:
        for path in ("/api/settings", "/api/jobs", "/api/jobs/prompts"):
            assert client.get(path).status_code == 403


def test_structured_retry_budget_and_cancellation() -> None:
    async def run() -> None:
        requests = []

        def handle(request: httpx.Request) -> httpx.Response:
            requests.append(json.loads(request.content))
            return sse({"ok": "invalid"}) if len(requests) == 1 else sse({"ok": True})

        gateway = Gateway(httpx.MockTransport(handle))
        endpoint = Endpoint(
            id=uuid4(), name="Test", provider="lm_studio", base_url="http://127.0.0.1:1234/v1"
        )
        profile = Profile(
            id=uuid4(),
            endpoint_id=endpoint.id,
            model="test",
            context_window=8192,
            max_output_tokens=512,
        )
        result = await gateway.structured(
            endpoint, profile, "JSON only", "Return ok true", ConnectionResult
        )
        assert result.ok and len(requests) == 2
        assert "validation errors" in requests[1]["messages"][-1]["content"]
        with pytest.raises(HTTPException) as budget:
            await gateway.structured(endpoint, profile, "JSON", "a" * 10000, ConnectionResult)
        assert budget.value.status_code == 422 and len(requests) == 2
        with pytest.raises(HTTPException):
            await Gateway(httpx.MockTransport(lambda r: sse({"bad": "data"}))).structured(
                endpoint, profile, "JSON", "ok", ConnectionResult
            )
        started = asyncio.Event()
        closed = asyncio.Event()

        class SlowStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                started.set()
                await asyncio.sleep(60)
                yield b"data: [DONE]\n\n"

            async def aclose(self):
                closed.set()

        slow = Gateway(httpx.MockTransport(lambda r: httpx.Response(200, stream=SlowStream())))
        task = asyncio.create_task(
            slow.structured(endpoint, profile, "JSON", "ok", ConnectionResult)
        )
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert closed.is_set() and slow.slots._value == 1

    asyncio.run(run())


def test_job_analysis_cache_sources_embeddings_and_retirement(database_url: str) -> None:
    calls = {"chat": 0, "embed": 0}

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "test-model"}]})
        if request.url.path.endswith("/embeddings"):
            calls["embed"] += 1
            return httpx.Response(200, json={"data": [{"embedding": [1.0, 0.5, 0.1]}]})
        calls["chat"] += 1
        return sse(ANALYSIS)

    with TestClient(create_app(Settings(database_url=database_url))) as client:
        client.app.state.gateway = Gateway(httpx.MockTransport(handle))
        endpoint, profile = configured(client)
        assert client.post(f"/api/settings/endpoints/{endpoint}/models").json()["models"] == [
            "test-model"
        ]
        assert (
            client.put(
                "/api/settings/assignments", json={"task": "embeddings", "profile_id": profile}
            ).status_code
            == 200
        )
        skill = client.post(
            "/api/career",
            json={"type": "skill", "name": "K8s", "category": "tool", "aliases": ["Kubernetes"]},
        ).json()
        job = client.post("/api/jobs", json={"title": "Engineer", "raw_text": TEXT}).json()
        assert client.get("/api/jobs").json()[0]["id"] == job["id"]

        def analyze():
            response = client.post(f"/api/jobs/{job['id']}/analyze", json={"use_embeddings": True})
            assert response.status_code == 200, response.text
            return response.json()

        first = analyze()
        assert first["cached"] is False and calls == {"chat": 1, "embed": 2}
        assert first["match"]["items"][0]["source_ref"]["entity_id"] == skill["id"]
        assert (
            "kubernetes" in first["match"]["strengths"]
            and "python" in first["match"]["missing_keywords"]
        )
        assert analyze()["cached"] is True and calls == {"chat": 1, "embed": 2}
        client.put(
            "/api/career/" + skill["id"],
            json={"type": "skill", "name": "Python", "category": "tool", "aliases": []},
        )
        changed = analyze()
        assert changed["match"]["career_snapshot_hash"] != first["match"]["career_snapshot_hash"]
        assert "python" in changed["match"]["strengths"] and calls == {"chat": 1, "embed": 3}
        client.delete("/api/career/skill/" + skill["id"])
        retired = analyze()
        assert retired["match"]["items"] == [] and retired["match"]["keyword_coverage"] == 0
        streamed = client.post(
            f"/api/jobs/{job['id']}/analyze/stream", json={"use_embeddings": False}
        )
        assert "event: progress" in streamed.text and "event: result" in streamed.text
        assert client.post(f"/api/jobs/{uuid4()}/analyze", json={}).status_code == 404
        engine = build_engine(database_url)
        with Session(engine) as db:
            assert len(list(db.scalars(select(Embedding)))) == 3
            assert len(list(db.scalars(select(AnalysisRecord)))) == 1
        engine.dispose()


def test_evidence_aliases_and_evaluation_contract() -> None:
    analysis = JobAnalysis.model_validate(ANALYSIS)
    validate_evidence(analysis, TEXT)
    with pytest.raises(ValueError):
        validate_evidence(analysis, "A different job description")
    assert contains("Used JS and K8s", "JavaScript", ALIASES)
    assert contains("Used .NET and C++", ".net", ALIASES)
    assert not contains("JavaScript", "Java", ALIASES)
    assert not contains("NoSQL", "SQL", ALIASES)
    assert not contains("C++ and C#", "C", ALIASES)
    assert contains("Used C++", "C++", ALIASES)
    assert not contains("CI", "CI/CD", ALIASES)
    assert contains("CI/CD", "continuous integration", ALIASES)
    cases = fixtures()
    assert 10 <= len(cases) <= 20
    assert assess(analysis, cases[0])
    for case in cases:
        valid = {
            **ANALYSIS,
            "required_skills": [{"term": term, "evidence": term} for term in case["required"]],
            "preferred_skills": [{"term": term, "evidence": term} for term in case["preferred"]],
            "responsibilities": [],
            "keywords": [],
            "seniority": {"term": case["seniority"], "evidence": case["seniority"]}
            if case["seniority"]
            else None,
            "years_experience": {"term": case["years"], "evidence": case["years"]}
            if case["years"]
            else None,
        }
        assert assess(JobAnalysis.model_validate(valid), case) == []


def test_explicit_job_metadata_uses_posting_quotes_without_inference() -> None:
    empty = JobAnalysis.model_validate({**ANALYSIS, "seniority": None, "years_experience": None})
    extracted = explicit_metadata(empty, "Senior Backend Engineer. Required experience: 5+ years.")
    assert extracted.seniority and extracted.seniority.evidence == "Senior"
    assert extracted.years_experience and extracted.years_experience.evidence == "5+ years"
    generic = explicit_metadata(empty, "Backend Engineer. Our company has 20 years of experience.")
    assert generic.seniority is None and generic.years_experience is None
    unrelated = explicit_metadata(
        empty, "Senior citizens are our customers. Our company was founded 5 years ago."
    )
    assert unrelated.seniority is None and unrelated.years_experience is None


def test_gateway_blocks_redirects_errors_changed_configuration_and_invalid_vectors() -> None:
    async def run() -> None:
        endpoint = Endpoint(
            id=uuid4(), name="Local", provider="lm_studio", base_url="http://127.0.0.1:1234/v1"
        )
        profile = Profile(id=uuid4(), endpoint_id=endpoint.id, model="test")
        calls = []

        def redirect(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return httpx.Response(302, headers={"Location": "https://remote.example/v1/models"})

        gateway = Gateway(httpx.MockTransport(redirect))
        with pytest.raises(HTTPException) as error:
            await gateway.models(endpoint)
        assert len(calls) == 1 and "remote.example" not in str(error.value.detail)
        stale = endpoint.model_copy(deep=True)
        endpoint.enabled = False
        gateway.configure(endpoint)
        with pytest.raises(HTTPException) as changed:
            await gateway.structured(stale, profile, "JSON", "test", ConnectionResult)
        assert changed.value.status_code == 409 and len(calls) == 1
        endpoint.enabled = True
        bad = Gateway(
            httpx.MockTransport(
                lambda r: httpx.Response(200, json={"data": [{"embedding": [0, 0]}]})
            )
        )
        with pytest.raises(HTTPException):
            await bad.embed(endpoint, profile, "text")

    asyncio.run(run())
