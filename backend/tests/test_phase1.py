import base64
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.models import User
from app.career.models import Achievement, Project
from app.core.config import Settings
from app.core.database import build_engine
from app.main import create_app
from app.resumes.models import Version
from app.resumes.schemas import ResumeDocument


def create(client: TestClient, data: dict) -> dict:
    response = client.post("/api/career", json=data)
    assert response.status_code == 201, response.text
    return response.json()


def document(template: str, source: dict | None = None) -> dict:
    return {
        "schema_version": 1,
        "header": {"name": "Ada Example", "email": "ada@example.test"},
        "sections": [
            {
                "key": str(uuid4()),
                "type": "experience" if source else "summary",
                "title": "Experience" if source else "Summary",
                "locked": True,
                "items": [
                    {
                        "key": str(uuid4()),
                        "text": "Reduced latency by 40% <script>alert(1)</script>",
                        "origin": "user",
                        "source_refs": [{"entity_type": "achievement", "entity_id": source["id"]}]
                        if source
                        else [],
                        "locked": True,
                    }
                ],
            }
        ],
        "metadata": {"template_id": template, "target_page_limit": 2, "style_overrides": {}},
    }


def test_full_career_crud_and_evidence(database_url: str) -> None:
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
        project = create(
            client, {"type": "project", "name": "Tool", "experience_id": experience["id"]}
        )
        achievement = create(
            client,
            {
                "type": "achievement",
                "experience_id": experience["id"],
                "text": "Reduced latency by 40%",
                "metric_value": "40",
                "metric_unit": "%",
                "metric_description": "latency reduction",
                "verified_by_user": True,
                "importance": 5,
            },
        )
        education = create(
            client, {"type": "education", "institution": "College", "degree": "BSc", "gpa": 3.8}
        )
        skill = create(
            client, {"type": "skill", "name": "Python", "aliases": ["Python 3"], "years_of_use": 5}
        )
        others = [
            {"type": "course", "education_id": education["id"], "name": "Databases"},
            {
                "type": "skill_evidence",
                "skill_id": skill["id"],
                "achievement_id": achievement["id"],
            },
            {"type": "certification", "name": "Certificate", "issuer": "Issuer"},
            {"type": "volunteer_experience", "organization": "Community", "title": "Mentor"},
            {"type": "award", "title": "Award"},
            {"type": "publication", "title": "Paper", "co_authors": ["Colleague"]},
            {
                "type": "custom_entry",
                "entry_type": "speaking",
                "payload": {"title": "Conference talk"},
            },
        ]
        for data in others:
            record = create(client, data)
            kind = data["type"]
            assert client.get(f"/api/career/{kind}/{record['id']}").json()["data"]["type"] == kind
            assert client.put(f"/api/career/{record['id']}", json=record["data"]).status_code == 200
            assert client.get(f"/api/career/{kind}").json()
            assert client.delete(f"/api/career/{kind}/{record['id']}").status_code == 204
            assert client.get(f"/api/career/{kind}").json() == []
        assert client.get("/api/career/forms").status_code == 200
        assert (
            client.post("/api/career", json={"type": "skill", "name": "PYTHON"}).status_code == 409
        )
        assert (
            client.post("/api/career", json={"type": "achievement", "text": "Invalid"}).status_code
            == 422
        )
        assert (
            client.post(
                "/api/career",
                json={
                    "type": "achievement",
                    "text": "Invalid",
                    "experience_id": experience["id"],
                    "project_id": project["id"],
                },
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/career",
                json={
                    "type": "experience",
                    "company": "X",
                    "job_title": "Y",
                    "start_date": "2024-01-01",
                    "end_date": "2020-01-01",
                },
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/career",
                json={"type": "course", "name": "Invalid", "education_id": str(uuid4())},
            ).status_code
            == 404
        )
        assert client.delete(f"/api/career/experience/{experience['id']}").status_code == 204
        assert client.get("/api/career/project").json() == []
        assert client.get("/api/career/achievement").json() == []


def test_owner_isolation_and_server_guard(database_url: str) -> None:
    engine = build_engine(database_url)
    owner, identifier = uuid4(), uuid4()
    with Session(engine) as session:
        session.add(User(id=owner, user_id=owner, display_name="Other owner", mode="local"))
        session.commit()
        session.add(
            Project(
                id=identifier,
                user_id=owner,
                name="Private",
                description="",
                challenges_solved="",
                results="",
            )
        )
        session.commit()
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        assert client.get(f"/api/career/project/{identifier}").status_code == 404
        assert (
            client.post(
                "/api/career",
                json={"type": "achievement", "project_id": str(identifier), "text": "Cross owner"},
            ).status_code
            == 404
        )
        assert (
            client.post(
                "/api/career",
                json={"type": "skill", "name": "Attack"},
                headers={"Origin": "https://untrusted.example"},
            ).status_code
            == 403
        )
    with TestClient(create_app(Settings(database_url=database_url, mode="server"))) as client:
        assert client.get("/api/resumes").status_code == 403
        assert client.get("/api/career/experience").status_code == 403
    with Session(engine) as session:
        from app.auth.repository import LOCAL_OWNER

        session.add(
            Achievement(
                user_id=LOCAL_OWNER,
                project_id=identifier,
                text="Cross owner",
                category="achievement",
                verified_by_user=False,
                importance=3,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    engine.dispose()


@pytest.mark.parametrize("template_key", ["classic", "modern"])
def test_master_versions_pdf_and_preview_parity(database_url: str, template_key: str) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        templates = client.get("/api/resumes/templates").json()
        template = next(t for t in templates if t["builtin_key"] == template_key)
        experience = create(
            client,
            {
                "type": "experience",
                "company": "Stored Employer",
                "job_title": "Stored Title",
                "start_date": "2020-01-01",
                "current": True,
            },
        )
        achievement = create(
            client,
            {
                "type": "achievement",
                "experience_id": experience["id"],
                "text": "Reduced latency by 40%",
            },
        )
        content = document(template["id"], achievement)
        content["sections"][0]["items"][0]["facts"] = {"employer": "FORGED", "title": "Invented"}
        response = client.post("/api/resumes", json={"title": "Master", "content": content})
        assert response.status_code == 201, response.text
        master = response.json()
        facts = master["content"]["sections"][0]["items"][0]["facts"]
        assert facts["employer"] == "Stored Employer" and facts["title"] == "Stored Title"
        preview = client.post("/api/resumes/preview", json=master["content"])
        assert preview.status_code == 200, preview.text
        preview_data = preview.json()
        pdf = client.get(f"/api/resumes/{master['id']}/pdf")
        assert pdf.status_code == 200
        assert pdf.headers["x-html-hash"] == preview_data["html_hash"]
        assert "<script>alert" not in preview_data["html"]
        assert "&lt;script&gt;" in preview_data["html"]
        preview_reader = PdfReader(BytesIO(base64.b64decode(preview_data["pdf_base64"])))
        reader = PdfReader(BytesIO(pdf.content))
        assert [page.get_contents().get_data() for page in reader.pages] == [
            page.get_contents().get_data() for page in preview_reader.pages
        ]
        assert (
            len(reader.pages) == preview_data["page_count"] == int(pdf.headers["x-page-count"]) == 1
        )
        assert [page.extract_text() for page in reader.pages] == [
            page.extract_text() for page in preview_reader.pages
        ]
        text = reader.pages[0].extract_text()
        assert "Stored Employer" in text and "Reduced latency by 40%" in text
        assert "FORGED" not in text
        assert float(reader.pages[0].mediabox.width) == pytest.approx(595.28, abs=1)
        content = master["content"]
        content["header"]["name"] = "Updated Name"
        updated = client.put(
            f"/api/resumes/{master['id']}",
            json={"title": "Master", "content": content, "expected_version": 1},
        )
        assert updated.status_code == 200 and updated.json()["version_number"] == 2
        assert (
            client.put(
                f"/api/resumes/{master['id']}",
                json={"title": "Stale", "content": content, "expected_version": 1},
            ).status_code
            == 409
        )
        assert client.get("/api/resumes").json()[0]["version_number"] == 2
        assert client.delete(f"/api/career/achievement/{achievement['id']}").status_code == 204
        assert client.get(f"/api/resumes/{master['id']}/pdf").status_code == 200
        assert client.post("/api/resumes/preview", json=content).status_code == 404
    engine = build_engine(database_url)
    with Session(engine) as session:
        versions = list(session.scalars(select(Version).order_by(Version.version_number)))
        assert len(versions) == 2
        assert versions[0].content_snapshot["header"]["name"] == "Ada Example"
        assert versions[0].content_snapshot["sections"][0]["locked"] is True
    engine.dispose()


def test_contract_validation_and_multi_page_count(database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        template = client.get("/api/resumes/templates").json()[0]["id"]
        content = document(template)
        item = content["sections"][0]["items"][0]
        item["origin"] = "ai"
        with pytest.raises(ValidationError):
            ResumeDocument.model_validate(content)
        item["origin"] = "user"
        content["sections"][0]["items"].append(dict(item))
        assert client.post("/api/resumes/preview", json=content).status_code == 422
        content["sections"][0]["items"] = [
            {
                **item,
                "key": str(uuid4()),
                "text": ("Built reliable systems and documented measurable outcomes. " * 5),
            }
            for _ in range(70)
        ]
        content["metadata"]["target_page_limit"] = 1
        preview = client.post("/api/resumes/preview", json=content)
        assert preview.status_code == 200, preview.text
        assert preview.json()["page_count"] > 1
        assert any("target is 1" in warning for warning in preview.json()["warnings"])
        content["metadata"]["style_overrides"] = {"font_size_pt": 1}
        assert client.post("/api/resumes/preview", json=content).status_code == 422
