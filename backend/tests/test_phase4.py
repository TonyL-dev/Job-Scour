import base64
import os
from uuid import uuid4

import pytest
from cryptography.exceptions import InvalidTag
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError, IntegrityError
from sqlalchemy.orm import Session
from test_phase1 import create, document

from app.applications.models import ApplicationRecord
from app.auth.models import User
from app.core.config import Settings
from app.core.database import build_engine
from app.jobs.repository import save_analysis
from app.jobs.schemas import JobAnalysis
from app.main import create_app
from app.privacy.encrypt_store import main as encrypt_store

TEMPLATE = "00000000-0000-4000-8000-000000000101"
OWNER = "00000000-0000-4000-8000-000000000001"


def master(client: TestClient) -> dict:
    r = client.post("/api/resumes", json={"title": "Original", "content": document(TEMPLATE)})
    assert r.status_code == 201, r.text
    return r.json()


def test_history_restore_duplicate_and_noop(database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        saved = master(client)
        request = {"title": saved["title"], "content": saved["content"], "expected_version": 1}
        assert client.put(f"/api/resumes/{saved['id']}", json=request).json()["version_number"] == 1
        request["content"]["header"]["name"] = "Changed name"
        request["autosave"] = True
        assert client.put(f"/api/resumes/{saved['id']}", json=request).json()["version_number"] == 2
        assert client.put(f"/api/resumes/{saved['id']}", json=request).status_code == 409
        versions = client.get(f"/api/resumes/{saved['id']}/versions").json()
        assert len(versions) == 2 and versions[0]["change_kind"] == "autosave"
        old = versions[-1]
        restored = client.post(
            f"/api/resumes/versions/{old['id']}/restore", json={"expected_version": 2}
        )
        assert restored.status_code == 200, restored.text
        assert restored.json()["version_number"] == 3
        assert restored.json()["content"]["header"]["name"] == "Ada Example"
        copy = client.post(
            f"/api/resumes/versions/{old['id']}/duplicate", json={"expected_version": 3}
        )
        assert copy.status_code == 201, copy.text
        assert copy.json()["id"] != saved["id"]
        assert copy.json()["parent_document_id"] == saved["id"]
        assert client.get(f"/api/resumes/versions/{old['id']}").json() == old
        assert client.get(f"/api/resumes/versions/{old['id']}/pdf").content.startswith(b"%PDF")
        assert client.get(f"/api/resumes/versions/{uuid4()}").status_code == 404


def test_ats_aliases_gaps_metrics_pdf_and_persistence(database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        experience = create(
            client,
            {
                "type": "experience",
                "company": "Example",
                "job_title": "Engineer",
                "start_date": "2020-01-01",
                "current": True,
            },
        )
        achievement = create(
            client,
            {
                "type": "achievement",
                "experience_id": experience["id"],
                "text": "Built JS services",
                "metric_value": "40",
                "metric_unit": "%",
            },
        )
        create(client, {"type": "skill", "name": "Python", "category": "language"})
        content = document(TEMPLATE, achievement)
        content["sections"][0]["items"][0]["text"] = "Helped with JS services"
        saved = client.post(
            "/api/resumes", json={"title": "ATS example", "content": content}
        ).json()
        version = client.get(f"/api/resumes/{saved['id']}/versions").json()[0]
        job = client.post(
            "/api/jobs",
            json={"raw_text": "Required JavaScript, Java and Python skills.", "title": "Developer"},
        ).json()
        with Session(client.app.state.engine) as db:
            from uuid import UUID

            analysis = save_analysis(
                db,
                UUID(OWNER),
                UUID(job["id"]),
                "synthetic",
                "synthetic",
                "fixture",
                JobAnalysis(
                    required_skills=[
                        {"term": t, "evidence": t} for t in ["JavaScript", "Java", "Python"]
                    ],
                    preferred_skills=[],
                    technologies=[],
                    responsibilities=[],
                    company_values=[],
                    industry_terms=[],
                    keywords=[],
                    seniority=None,
                    years_experience=None,
                ),
            )
        result = client.post(
            "/api/ats/reports", json={"version_id": version["id"], "analysis_id": str(analysis.id)}
        )
        assert result.status_code == 201, result.text
        report = result.json()
        assert report["page_count"] == 1
        assert report["matched_keywords"] == ["javascript"]
        assert report["sub_scores"]["keywords"] == 33.3
        assert report["sub_scores"]["parseability"] == 100
        findings = report["findings"]
        assert any(f["code"] == "skill_gap" and "java:" in f["message"] for f in findings)
        assert any(f["code"] == "available_keyword" and f["source_refs"] for f in findings)
        metric = next(f for f in findings if f["code"] == "available_metric")
        assert metric["item_key"] == content["sections"][0]["items"][0]["key"]
        assert client.get(f"/api/ats/reports/{version['id']}").json() == [report]
        assert client.get("/api/jobs/analyses").json()[0]["id"] == str(analysis.id)
        assert (
            client.post(
                "/api/ats/reports", json={"version_id": version["id"], "analysis_id": str(uuid4())}
            ).status_code
            == 404
        )


def test_tracker_exact_versions_cas_and_ownership(database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        saved = master(client)
        version = client.get(f"/api/resumes/{saved['id']}/versions").json()[0]
        body = {
            "company": "Example",
            "position": "Engineer",
            "version_id": version["id"],
            "notes": "Synthetic application",
            "follow_up_date": "2026-10-07",
        }
        r = client.post("/api/applications", json=body)
        assert r.status_code == 201, r.text
        application = r.json()
        event = {
            "stage": "interview",
            "date": "2026-10-07",
            "notes": "Round one",
            "expected_revision": 1,
        }
        assert (
            client.post(f"/api/applications/{application['id']}/events", json=event).json()[
                "revision"
            ]
            == 2
        )
        assert (
            client.post(f"/api/applications/{application['id']}/events", json=event).status_code
            == 409
        )
        assert len(client.get(f"/api/applications/{application['id']}/events").json()) == 2
        assert (
            client.put(
                f"/api/resumes/{saved['id']}",
                json={"title": "New title", "content": saved["content"], "expected_version": 1},
            ).status_code
            == 200
        )
        assert client.get("/api/applications").json()[0]["version_id"] == version["id"]
        body["version_id"] = str(uuid4())
        assert client.post("/api/applications", json=body).status_code == 404
        engine = client.app.state.engine
        from uuid import UUID

        with Session(engine) as db:
            owner = uuid4()
            db.add(User(id=owner, user_id=owner, display_name="Other owner", mode="local"))
            db.commit()
            db.add(
                ApplicationRecord(
                    user_id=owner,
                    version_id=UUID(version["id"]),
                    company="Other",
                    position="Other",
                    stage="saved",
                    channel="",
                    notes="",
                    follow_up_done=False,
                )
            )
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()


def test_passcode_export_delete_restart_and_origins(database_url: str) -> None:
    app = create_app(Settings(database_url=database_url))
    with TestClient(app) as client:
        saved = master(client)
        skill = create(client, {"type": "skill", "name": "Python", "category": "language"})
        assert client.delete(f"/api/career/skill/{skill['id']}").status_code == 204
        exported = client.get("/api/privacy/export").json()
        assert exported["tables"]["skills"][0]["deleted_at"]
        assert exported["tables"]["resume_versions"]
        assert "password_hash" not in str(exported)
        assert (
            client.post("/api/privacy/passcode", json={"passcode": "secret passcode"}).status_code
            == 200
        )
        assert (
            client.post("/api/privacy/passcode", json={"passcode": "changed passcode"}).status_code
            == 401
        )
        assert client.post("/api/privacy/lock").json()["locked"] is True
        for path in ["/api/career/history", "/api/resumes", "/api/jobs", "/api/privacy/export"]:
            assert client.get(path).status_code == 423
        denied = client.post(
            "/api/privacy/unlock",
            json={"passcode": "secret passcode"},
            headers={"Origin": "https://hostile.example"},
        )
        assert denied.status_code == 403
        assert client.post("/api/privacy/unlock", json={"passcode": "wrong"}).status_code == 401
        app.state.lock.retry_at = 0
        r = client.post("/api/privacy/unlock", json={"passcode": "secret passcode"})
        assert r.status_code == 200 and "HttpOnly" in r.headers["set-cookie"]
        assert (
            client.post("/api/privacy/delete-all", json={"confirmation": "wrong"}).status_code
            == 422
        )
        assert client.get(f"/api/resumes/{saved['id']}").status_code == 200
        assert (
            client.post(
                "/api/privacy/delete-all", json={"confirmation": "DELETE ALL MY DATA"}
            ).status_code
            == 204
        )
        assert all(not rows for rows in client.get("/api/privacy/export").json()["tables"].values())
        assert client.get("/api/privacy/status").json()["passcode_enabled"]
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        assert client.get("/api/privacy/status").json()["locked"]
        assert client.get("/api/resumes").status_code == 423


def test_encrypted_store_conversion_keys_and_tamper(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        saved = master(client)
        create(client, {"type": "skill", "name": "UniqueSecretSkill", "category": "language"})
        old = client.get(f"/api/resumes/{saved['id']}/versions").json()[0]
    secret = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("APP_ENCRYPTION_KEY", secret)
    encrypt_store()
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        assert client.get(f"/api/resumes/{saved['id']}/versions").json()[0] == old
        assert client.get("/api/privacy/status").json()["encryption_enabled"]
        assert client.get("/api/career/skill").status_code == 200
        raw = client.app.state.engine.raw_connection()
        assert (
            raw.execute("SELECT name, normalized_name FROM skills")
            .fetchone()[0]
            .startswith("stonks:aesgcm:1:")
        )
        assert (
            raw.execute("SELECT normalized_name FROM skills")
            .fetchone()[0]
            .startswith("stonks:hmac:1:")
        )
        raw.close()
        create(client, {"type": "skill", "name": "EncryptedSecondSkill", "category": "language"})
        assert (
            client.get("/api/privacy/export").json()["tables"]["skills"][0]["name"]
            == "UniqueSecretSkill"
        )
    monkeypatch.delenv("APP_ENCRYPTION_KEY")
    with pytest.raises(RuntimeError, match="requires APP_ENCRYPTION_KEY"):
        with TestClient(create_app(Settings(database_url=database_url))):
            pass
    monkeypatch.setenv("APP_ENCRYPTION_KEY", base64.b64encode(os.urandom(32)).decode())
    with pytest.raises(InvalidTag):
        with TestClient(create_app(Settings(database_url=database_url))):
            pass
    monkeypatch.setenv("APP_ENCRYPTION_KEY", secret)
    engine = build_engine(database_url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE skills SET name = replace(name, 'stonks:aesgcm:1:', 'stonks:aesgcm:1:AAAA')"
            )
        )
    engine.dispose()
    with pytest.raises(InvalidTag):
        with TestClient(create_app(Settings(database_url=database_url))):
            pass


def test_sqlcipher_complete_database_and_passphrase(
    database_url: str, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    from pathlib import Path

    from sqlalchemy.engine import make_url

    from app.privacy.encrypt_database import convert

    with TestClient(create_app(Settings(database_url=database_url))) as client:
        saved = master(client)
    source = Path(str(make_url(database_url).database))
    target = tmp_path / "encrypted.db"
    convert(source, target, "strong database passphrase")
    assert target.read_bytes()[:16] != b"SQLite format 3\x00"
    assert b"Ada Example" not in target.read_bytes()
    assert source.read_bytes()[:16] == b"SQLite format 3\x00"
    url = f"sqlite:///{target}"
    monkeypatch.setenv("APP_DATABASE_PASSPHRASE", "strong database passphrase")
    with TestClient(create_app(Settings(database_url=url))) as client:
        assert client.get(f"/api/resumes/{saved['id']}").json() == saved
        assert client.get("/api/privacy/status").json()["database_encrypted"]
        assert client.get(f"/api/resumes/{saved['id']}/pdf").content.startswith(b"%PDF")
        assert (
            client.post(
                "/api/privacy/delete-all", json={"confirmation": "DELETE ALL MY DATA"}
            ).status_code
            == 204
        )
    monkeypatch.setenv("APP_DATABASE_PASSPHRASE", "incorrect passphrase")
    with pytest.raises(RuntimeError, match="Cannot unlock"):
        with TestClient(create_app(Settings(database_url=url))):
            pass
    monkeypatch.delenv("APP_DATABASE_PASSPHRASE")
    with pytest.raises(DatabaseError):
        with TestClient(create_app(Settings(database_url=url))):
            pass


def test_tailored_manual_edits_preserve_ai_boundary_and_old_versions(database_url: str) -> None:
    from test_phase3 import generate, install, setup, transport

    with TestClient(create_app(Settings(database_url=database_url))) as client:
        master, job = setup(client)
        install(client, transport())
        run = generate(client, master, job)
        choices = [
            {"suggestion_id": s["id"], "action": "accept"}
            for s in run["suggestions"]
            if s["verification"] == "supported"
        ]
        saved = client.post(
            f"/api/generation/{run['id']}/commit", json={"title": "Tailored", "decisions": choices}
        ).json()
        old = client.get(f"/api/resumes/{saved['id']}/versions").json()[0]
        content = saved["content"]
        item = content["sections"][0]["items"][0]
        assert item["origin"] == "ai"
        item["text"] = "Invented Kubernetes work"
        request = {"title": "Tailored", "content": content, "expected_version": 1}
        assert client.put(f"/api/resumes/{saved['id']}", json=request).status_code == 422
        item["text"] = "Built Python APIs and reduced latency by 40%."
        item["origin"] = "user"
        preview = client.post(f"/api/resumes/{saved['id']}/preview", json=content)
        assert preview.status_code == 200, preview.text
        edited = client.put(f"/api/resumes/{saved['id']}", json=request)
        assert edited.status_code == 200, edited.text
        assert edited.json()["version_number"] == 2 and edited.json()["kind"] == "tailored"
        assert client.get(f"/api/resumes/versions/{old['id']}").json() == old
        repeated = client.post(
            f"/api/generation/{run['id']}/commit", json={"title": "Tailored", "decisions": choices}
        ).json()
        assert repeated["version_number"] == 1 and repeated["content"] == old["content"]
        assert client.get(f"/api/generation/{run['id']}").json()["saved_version_id"] == old["id"]
        assert client.get(f"/api/resumes/{master['id']}").json() == master


def test_delete_revokes_inflight_analysis_and_pending_writes(database_url: str) -> None:
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from uuid import UUID

    import httpx
    from fastapi import HTTPException
    from test_phase2 import ANALYSIS, configured, sse

    from app.ai.gateway import Gateway
    from app.career.models import Skill
    from app.core.workspace import bind

    started, release = Event(), Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        started.set()
        await asyncio.to_thread(release.wait)
        return sse(ANALYSIS)

    with TestClient(create_app(Settings(database_url=database_url))) as client:
        configured(client)
        client.app.state.gateway = Gateway(httpx.MockTransport(handler))
        job = client.post(
            "/api/jobs",
            json={"raw_text": "Required: Python and Kubernetes. Preferred: SQL. Build APIs."},
        ).json()
        with Session(client.app.state.engine) as pending:
            bind(pending, client.app.state.barrier)
            pending.add(
                Skill(
                    user_id=UUID(OWNER),
                    name="LateSkill",
                    category="tool",
                    aliases=[],
                    normalized_name="lateskill",
                )
            )
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(client.post, f"/api/jobs/{job['id']}/analyze", json={})
                try:
                    assert started.wait(10)
                    assert (
                        client.post(
                            "/api/privacy/delete-all", json={"confirmation": "DELETE ALL MY DATA"}
                        ).status_code
                        == 204
                    )
                finally:
                    release.set()
                response = future.result(timeout=10)
                assert response.status_code == 423, response.text
            with pytest.raises(HTTPException) as revoked:
                pending.commit()
            assert revoked.value.status_code == 423
            pending.rollback()
        assert all(not rows for rows in client.get("/api/privacy/export").json()["tables"].values())
