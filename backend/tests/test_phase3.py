import json
import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from test_phase1 import create, document
from test_phase2 import ANALYSIS, configured, sse

from app.ai.gateway import Gateway
from app.ai.generation import claim_check, source_text
from app.career.schemas import Achievement, CareerRecord
from app.core.config import Settings
from app.core.database import build_engine
from app.main import create_app
from app.resumes import generation_repository as repo
from app.resumes.generation_models import GenerationRecord
from app.resumes.generation_service import reorder_unlocked
from app.resumes.schemas import Item


def setup(client: TestClient, *, locked: bool = False, count: int = 1) -> tuple[dict, dict]:
    _, profile = configured(client)
    for task in ("ranking", "rewriting", "summary", "verification", "condensing"):
        assert (
            client.put(
                "/api/settings/assignments", json={"task": task, "profile_id": profile}
            ).status_code
            == 200
        )
    experience = client.post(
        "/api/career",
        json={
            "type": "experience",
            "company": "Stored Employer",
            "job_title": "Stored Title",
            "start_date": "2020-01-01",
            "current": True,
        },
    ).json()
    achievement = client.post(
        "/api/career",
        json={
            "type": "achievement",
            "experience_id": experience["id"],
            "text": "Built Python APIs and reduced latency by 40%.",
            "importance": 5,
        },
    ).json()
    content = {
        "schema_version": 1,
        "header": {"name": "Synthetic Candidate"},
        "sections": [
            {
                "key": str(uuid4()),
                "type": "experience",
                "title": "Experience",
                "locked": locked,
                "items": [
                    {
                        "key": str(uuid4()),
                        "text": "Built Python APIs and reduced latency by 40%.",
                        "origin": "user",
                        "source_refs": [
                            {"entity_type": "achievement", "entity_id": achievement["id"]}
                        ],
                        "locked": n == 0 and count > 1,
                    }
                    for n in range(count)
                ],
            }
        ],
        "metadata": {"template_id": "00000000-0000-4000-8000-000000000101", "target_page_limit": 2},
    }
    master = client.post(
        "/api/resumes",
        json={"title": "Synthetic master", "gold_standard": True, "content": content},
    ).json()
    job = client.post(
        "/api/jobs",
        json={
            "title": "API Developer",
            "raw_text": "Required: Python and Kubernetes. Preferred: SQL. Build APIs.",
        },
    ).json()
    return master, job


def transport(*, unsupported: bool = False, partial: bool = False) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        kind = payload["response_format"]["json_schema"]["name"]
        if kind == "JobAnalysis":
            return sse(ANALYSIS)
        context = json.loads(payload["messages"][1]["content"].split("DATA:\n")[1])
        if kind == "Selection":
            return sse(
                {
                    "choices": [
                        {"source_id": c["source_id"], "reason": "Relevant Python evidence"}
                        for c in context["candidates"][:4]
                    ]
                }
            )
        if kind == "Rewrite":
            return sse(
                {
                    "text": "Built Python APIs; reduced latency by 400%."
                    if unsupported
                    else "Reduced latency by 40% using Python APIs.",
                    "source_ids": list(context["sources"]),
                }
            )
        assert kind == "Verification"
        assert payload["temperature"] == 0
        return sse(
            {
                "status": "partially_supported" if partial else "supported",
                "reason": "Source comparison",
            }
        )

    return httpx.MockTransport(handler)


def install(client: TestClient, mock: httpx.MockTransport) -> None:
    gateway = Gateway(mock)
    client.app.state.gateway = gateway
    client.app.state.runs.gateway = gateway


def wait(client: TestClient, identifier: str) -> dict:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        run = client.get(f"/api/generation/{identifier}").json()
        if run["status"] not in {"queued", "running"}:
            return run
        time.sleep(0.05)
    raise AssertionError("Run did not finish")


def generate(client: TestClient, master: dict, job: dict, **extra: object) -> dict:
    response = client.post(
        "/api/generation",
        json={"master_id": master["id"], "job_id": job["id"], "use_embeddings": False, **extra},
    )
    assert response.status_code == 202, response.text
    return wait(client, response.json()["id"])


def test_generation_review_and_real_pdf(database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        master, job = setup(client)
        install(client, transport())
        run = generate(client, master, job)
        assert run["status"] == "succeeded", run
        assert run["page_count"] <= 2 and len(run["suggestions"]) == 1
        suggestion = run["suggestions"][0]
        assert suggestion["verification"] == "supported"
        assert (
            run["proposed"]["metadata"]["template_id"]
            == master["content"]["metadata"]["template_id"]
        )
        body = {
            "decisions": [{"suggestion_id": suggestion["id"], "action": "accept"}],
            "expected_revision": 0,
        }
        preview = client.post(f"/api/generation/{run['id']}/preview", json=body)
        assert preview.status_code == 200, preview.text
        assert "Stored Employer" in preview.json()["html"]
        assert "Stored Title" in preview.json()["html"]
        saved = client.post(
            f"/api/generation/{run['id']}/commit", json={**body, "title": "Tailored"}
        )
        assert saved.status_code == 201, saved.text
        assert saved.json()["kind"] == "tailored"
        assert client.get(f"/api/resumes/{master['id']}").json() == master
        exported = client.get(f"/api/resumes/{saved.json()['id']}/pdf")
        assert exported.content.startswith(b"%PDF")
        assert exported.headers["X-HTML-Hash"] == preview.json()["html_hash"]
        assert "event: result" in client.get(f"/api/generation/{run['id']}/events?after=1").text
        assert (
            client.post(
                f"/api/generation/{run['id']}/commit", json={**body, "title": "Again"}
            ).json()["id"]
            == saved.json()["id"]
        )


@pytest.mark.parametrize("unsupported,partial", [(True, False), (False, True)])
def test_unsupported_suggestions_default_excluded(
    database_url: str, unsupported: bool, partial: bool
) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        master, job = setup(client)
        install(client, transport(unsupported=unsupported, partial=partial))
        run = generate(client, master, job)
        assert run["status"] == "succeeded", run
        assert run["proposed"]["sections"] == master["content"]["sections"]
        suggestion = run["suggestions"][0]
        assert suggestion["verification"] != "supported"
        assert (
            client.post(
                f"/api/generation/{run['id']}/preview",
                json={"decisions": [{"suggestion_id": suggestion["id"], "action": "accept"}]},
            ).status_code
            == 422
        )
        edited = client.post(
            f"/api/generation/{run['id']}/commit",
            json={
                "title": "User confirmed",
                "decisions": [
                    {
                        "suggestion_id": suggestion["id"],
                        "action": "edit",
                        "text": "Built Python APIs.",
                    }
                ],
            },
        )
        assert edited.status_code == 201, edited.text
        assert edited.json()["content"]["sections"][0]["items"][0]["origin"] == "user"


def test_locks_partial_regeneration_review_conflicts_and_retirement(database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        master, job = setup(client, locked=True)
        install(client, transport())
        run = generate(client, master, job)
        assert run["status"] == "succeeded" and not run["suggestions"]
        assert run["proposed"]["sections"] == master["content"]["sections"]
        assert (
            client.put(f"/api/generation/{run['id']}/review", json={"decisions": []}).status_code
            == 200
        )
        assert (
            client.put(f"/api/generation/{run['id']}/review", json={"decisions": []}).status_code
            == 409
        )
        ref = master["content"]["sections"][0]["items"][0]["source_refs"][0]
        client.delete(f"/api/career/achievement/{ref['entity_id']}")
        assert (
            client.post(
                f"/api/generation/{run['id']}/commit",
                json={"title": "Retired", "expected_revision": 1},
            ).status_code
            == 409
        )


def test_cancel_and_recovery_preserve_durable_run(database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        master, job = setup(client)

        async def blocked(request: httpx.Request) -> httpx.Response:
            import asyncio

            await asyncio.sleep(60)
            return sse(ANALYSIS)

        install(client, httpx.MockTransport(blocked))
        response = client.post(
            "/api/generation",
            json={"master_id": master["id"], "job_id": job["id"], "use_embeddings": False},
        )
        identifier = response.json()["id"]
        result = client.post(f"/api/generation/{identifier}/cancel")
        assert result.status_code == 200 and result.json()["status"] == "cancelled"
    engine = build_engine(database_url)
    with Session(engine) as db:
        row = db.get(GenerationRecord, UUID(identifier))
        assert row is not None
        row.status = "running"
        db.commit()
    repo.recover(engine)
    with Session(engine) as db:
        row = db.get(GenerationRecord, UUID(identifier))
        assert row is not None and row.status == "failed"
    engine.dispose()


def test_claim_checks_numbers_aliases_and_invented_technology() -> None:
    identifier = uuid4()
    sources = {identifier: "Built Python APIs; reduced latency by 40%. Kubernetes (K8s)."}
    assert (
        claim_check("Reduced latency by 40% using Python APIs.", sources, [identifier], []) is None
    )
    assert claim_check("Reduced latency by 400%.", sources, [identifier], [])
    assert claim_check("Built Rust APIs.", sources, [identifier], [])
    assert claim_check("Built Rust-based APIs.", sources, [identifier], [])
    assert (
        claim_check(
            "Developed Python-based APIs to decrease response time by 40%.",
            sources,
            [identifier],
            [],
        )
        is None
    )
    assert claim_check("Led Python teams.", sources, [identifier], [])
    assert claim_check("Built Python APIs.", sources, [uuid4()], [])
    assert (
        claim_check(
            "Managed AWS workloads.",
            {identifier: "Managed Amazon Web Services workloads."},
            [identifier],
            ["AWS"],
        )
        is None
    )


def test_skill_ordering_preserves_locked_positions() -> None:
    items = [
        Item(key=uuid4(), text=f"Skill {n}", origin="user", source_refs=[], locked=n == 1)
        for n in range(4)
    ]
    reordered = reorder_unlocked(items, [i.key for i in reversed(items)])
    assert reordered[1] == items[1]
    assert [i.text for i in reordered] == ["Skill 3", "Skill 1", "Skill 2", "Skill 0"]


def test_only_factual_numbers_and_stored_metrics_prove_claims() -> None:
    identifier = uuid4()
    record = CareerRecord(
        id=identifier,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        deleted_at=None,
        data=Achievement(
            experience_id=uuid4(),
            text="Used Python for 3 years. Reduced latency.",
            importance=5,
            metric_value="40.0000",
            metric_unit="%",
            metric_description="latency reduction",
        ),
    )
    evidence = {identifier: source_text(record)}
    assert (
        "importance" not in evidence[identifier] and "verified_by_user" not in evidence[identifier]
    )
    assert claim_check("Used Python for 5 years.", evidence, [identifier], [])
    assert claim_check("Reduced latency by 40%.", evidence, [identifier], []) is None
    assert claim_check("Reduced latency by 400%.", evidence, [identifier], [])
    assert claim_check("Reduced latency by -40%.", evidence, [identifier], [])


@pytest.mark.parametrize("visible", [True, False])
def test_summary_uses_visible_education_sources_and_preserves_locks(
    database_url: str, visible: bool
) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        _, profile = configured(client)
        for task in ("ranking", "rewriting", "summary", "verification", "condensing"):
            client.put("/api/settings/assignments", json={"task": task, "profile_id": profile})
        school = client.post(
            "/api/career", json={"type": "education", "institution": "College", "degree": "BSc"}
        ).json()
        content = {
            "schema_version": 1,
            "header": {"name": "Graduate"},
            "sections": [
                {"key": str(uuid4()), "type": "summary", "title": "Summary", "items": []},
                {
                    "key": str(uuid4()),
                    "type": "education",
                    "title": "Education",
                    "visible": visible,
                    "locked": True,
                    "items": [
                        {
                            "key": str(uuid4()),
                            "text": "BSc from College.",
                            "origin": "user",
                            "source_refs": [
                                {"entity_type": "education", "entity_id": school["id"]}
                            ],
                        }
                    ],
                },
            ],
            "metadata": {"template_id": "00000000-0000-4000-8000-000000000101"},
        }
        master = client.post("/api/resumes", json={"title": "Graduate", "content": content}).json()
        job = client.post(
            "/api/jobs",
            json={"raw_text": "Required: Python and Kubernetes. Preferred: SQL. Build APIs."},
        ).json()

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            schema = payload["response_format"]["json_schema"]["name"]
            if schema == "JobAnalysis":
                return sse(ANALYSIS)
            if schema == "Selection":
                return sse({"choices": []})
            if schema == "Verification":
                return sse({"status": "supported", "reason": "Stored degree and institution"})
            assert schema == "Rewrite"
            context = json.loads(payload["messages"][1]["content"].split("DATA:\n")[1])
            return sse({"text": "BSc from College.", "source_ids": list(context["sources"])})

        install(client, httpx.MockTransport(handler))
        run = generate(client, master, job)
        assert run["status"] == "succeeded", run
        assert run["proposed"]["sections"][1] == master["content"]["sections"][1]
        assert bool(run["proposed"]["sections"][0]["items"]) == visible


def test_partial_regeneration_and_review_lock_updates(database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        master, job = setup(client, count=3)
        install(client, transport())
        section = master["content"]["sections"][0]
        target = section["items"][1]["key"]
        run = generate(client, master, job, item_keys=[target], preset="concise")
        assert run["status"] == "succeeded", run
        assert {s["item_key"] for s in run["suggestions"]} == {target}
        assert run["proposed"]["sections"][0]["items"][0] == section["items"][0]
        assert run["proposed"]["sections"][0]["items"][2] == section["items"][2]
        saved = client.put(f"/api/generation/{run['id']}/review", json={"locks": {target: True}})
        assert saved.status_code == 200, saved.text
        child = generate(client, master, job, parent_run_id=run["id"], item_keys=[target])
        assert child["status"] == "succeeded" and not child["suggestions"]
        assert child["base"]["sections"][0]["items"][1]["locked"]


def test_long_master_budget_and_actual_page_fitting(database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        master, job = setup(client, count=30)
        content = master["content"]
        for item in content["sections"][0]["items"]:
            item["text"] *= 12
        saved = client.put(
            f"/api/resumes/{master['id']}",
            json={"title": master["title"], "content": content, "expected_version": 1},
        ).json()
        assert int(client.get(f"/api/resumes/{saved['id']}/pdf").headers["X-Page-Count"]) > 2
        install(client, transport())
        run = generate(client, saved, job)
        assert run["status"] == "succeeded", run
        assert run["page_count"] <= 2
        assert (
            run["proposed"]["sections"][0]["items"][0]
            == saved["content"]["sections"][0]["items"][0]
        )
        assert any(
            s["proposed"] is None and s["verification"] == "supported" for s in run["suggestions"]
        )


def test_generation_owner_and_server_guards(database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=database_url, mode="server"))) as client:
        assert client.get("/api/generation").status_code == 403
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        assert client.get(f"/api/generation/{uuid4()}").status_code == 404
        assert (
            client.post(
                "/api/generation",
                headers={"Origin": "https://untrusted.example"},
                json={"master_id": str(uuid4()), "job_id": str(uuid4())},
            ).status_code
            == 403
        )


def test_phase3_migration_preserves_existing_master_snapshots(database_url: str) -> None:
    config = Config("alembic.ini")
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        configured(client)
        experience = create(
            client,
            {
                "type": "experience",
                "company": "Legacy",
                "job_title": "Engineer",
                "start_date": "2020-01-01",
            },
        )
        source = create(
            client,
            {
                "type": "achievement",
                "experience_id": experience["id"],
                "text": "Reduced latency by 40%",
            },
        )
        content = document("00000000-0000-4000-8000-000000000101", source)
        response = client.post(
            "/api/resumes", json={"title": "Existing master", "content": content}
        )
        assert response.status_code == 201
        master = response.json()
    # Seed under the current app, then project onto the historical schema before upgrade.
    # Current ORM columns must never be used against a deliberately old database.
    command.downgrade(config, "171010dacb0f")
    command.upgrade(config, "head")
    command.check(config)
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        assert client.get(f"/api/resumes/{master['id']}").json() == master
        assert client.get(f"/api/career/achievement/{source['id']}").status_code == 200
