import base64
import io
import zipfile
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.repository import LOCAL_OWNER
from app.core.config import Settings
from app.importers import repository as imports
from app.importers.parser import parse
from app.importers.schemas import Fragment
from app.main import create_app
from app.rendering.docx import export as export_docx
from app.rendering.service import render
from app.resumes.schemas import ResumeDocument, SourceRef


def docx(text: str, extra: dict[str, bytes] | None = None) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as bundle:
        bundle.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        )
        bundle.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>'
            + text
            + "</w:t></w:r></w:p></w:body></w:document>",
        )
        for name, value in (extra or {}).items():
            bundle.writestr(name, value)
    return output.getvalue()


def upload(
    client: TestClient, text: str = "Orbit project reduced latency by 40%", retain: bool = False
) -> dict:
    response = client.post(
        "/api/imports",
        json={
            "filename": "resume.docx",
            "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "content_base64": base64.b64encode(docx(text)).decode(),
            "retain_original": retain,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def candidate(key: str, data: dict) -> dict:
    return {
        "key": key,
        "data": data,
        "locator": "paragraph 1",
        "excerpt": "Orbit project reduced latency by 40%",
        "decision": "accepted",
        "user_supplied": True,
    }


def test_atomic_import_review_and_replay(database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        run = upload(client)
        identifier = run["id"]
        candidates = [
            candidate(
                "parent", {"type": "project", "name": "Orbit", "description": "Latency project"}
            ),
            candidate(
                "child",
                {
                    "type": "achievement",
                    "project_id": "@parent",
                    "text": "Reduced latency by 40%",
                    "metric_value": "40",
                    "metric_unit": "%",
                },
            ),
        ]
        review = client.put(
            f"/api/imports/{identifier}", json={"expected_revision": 1, "candidates": candidates}
        )
        assert review.status_code == 200, review.text
        assert client.post(f"/api/imports/{identifier}/commit?revision=1").status_code == 409
        commit = client.post(f"/api/imports/{identifier}/commit?revision=2")
        assert commit.status_code == 200, commit.text
        assert len(commit.json()["saved_ids"]) == 2
        replay = client.post(f"/api/imports/{identifier}/commit?revision=2")
        assert replay.json() == commit.json()
        assert len(client.get("/api/career/project").json()) == 1
        assert len(client.get("/api/career/achievement").json()) == 1


def test_import_rollback_source_and_discard(database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        run = upload(client)
        identifier = run["id"]
        candidates = [
            candidate("parent", {"type": "project", "name": "Orbit"}),
            candidate(
                "child",
                {"type": "achievement", "project_id": "@missing", "text": "Reduced latency"},
            ),
        ]
        assert (
            client.put(
                f"/api/imports/{identifier}",
                json={"expected_revision": 1, "candidates": candidates},
            ).status_code
            == 200
        )
        assert client.post(f"/api/imports/{identifier}/commit?revision=2").status_code == 422
        assert client.get("/api/career/project").json() == []
        assert client.get(f"/api/imports/{identifier}").json()["revision"] == 2
        candidates[0]["excerpt"] = "Invented source"
        assert (
            client.put(
                f"/api/imports/{identifier}",
                json={"expected_revision": 2, "candidates": candidates},
            ).status_code
            == 422
        )
        assert (
            client.post(f"/api/imports/{identifier}/discard?revision=2").json()["status"]
            == "discarded"
        )
        assert client.get(f"/api/imports/{uuid4()}").status_code == 404


def test_upload_encryption_export_and_deletion(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_UPLOAD_KEY", base64.b64encode(b"k" * 32).decode())
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        run = upload(client, retain=True)
        identifier = run["id"]
        original = client.get(f"/api/imports/{identifier}/original")
        assert original.status_code == 200 and original.content.startswith(b"PK")
        assert client.get("/api/privacy/export").status_code == 200
        monkeypatch.setenv("APP_UPLOAD_KEY", base64.b64encode(b"w" * 32).decode())
        assert client.get(f"/api/imports/{identifier}/original").status_code == 503
        assert client.delete(f"/api/imports/{identifier}/original").status_code == 204
        assert client.get(f"/api/imports/{identifier}/original").status_code == 404


@pytest.mark.parametrize(
    "extra",
    [
        {"../bad.xml": b"<bad/>"},
        {"word/vbaProject.bin": b"bad"},
        {"word/evil.xml": b'<!DOCTYPE x [<!ENTITY a "bad">]><x>&a;</x>'},
        {
            "word/_rels/document.xml.rels": (
                b'<Relationships><Relationship Type="externalTemplate" '
                b'TargetMode="External" Target="https://evil.example"/></Relationships>'
            )
        },
    ],
)
def test_docx_rejects_active_and_unsafe_content(extra: dict[str, bytes]) -> None:
    with pytest.raises(ValueError):
        parse(docx("Synthetic", extra), "docx")


def test_signature_ocr_size_and_archive_bounds() -> None:
    with pytest.raises(ValueError):
        parse(b"not a pdf", "pdf")
    with pytest.raises(ValueError):
        parse(b"x" * (2 * 1024 * 1024 + 1), "docx")
    with pytest.raises(ValueError):
        parse(docx(""), "docx")
    with pytest.raises(ValueError):
        parse(docx("Synthetic", {f"item{n}": b"" for n in range(257)}), "docx")


@pytest.mark.parametrize("kind", ["pdf", "docx"])
def test_real_document_import_all_core_facts_and_master_pdf(database_url, kind):
    example = ResumeDocument.model_validate(
        {
            "schema_version": 1,
            "header": {"name": "Imported Candidate"},
            "sections": [
                {
                    "key": str(uuid4()),
                    "type": "experience",
                    "title": "Experience",
                    "items": [
                        {
                            "key": str(uuid4()),
                            "text": "Built Python APIs and reduced latency by 40%.",
                            "origin": "user",
                            "source_refs": [],
                            "facts": {
                                "employer": "Orbit Ltd",
                                "title": "API Developer",
                                "start_date": "2020-01-01",
                            },
                        }
                    ],
                },
                {
                    "key": str(uuid4()),
                    "type": "projects",
                    "title": "Projects",
                    "items": [
                        {
                            "key": str(uuid4()),
                            "text": "Orbit project built Python APIs.",
                            "origin": "user",
                            "source_refs": [],
                        }
                    ],
                },
                {
                    "key": str(uuid4()),
                    "type": "education",
                    "title": "Education",
                    "items": [
                        {
                            "key": str(uuid4()),
                            "text": "Example University Bachelor Computer Science",
                            "origin": "user",
                            "source_refs": [],
                        }
                    ],
                },
                {
                    "key": str(uuid4()),
                    "type": "skills",
                    "title": "Skills",
                    "items": [
                        {"key": str(uuid4()), "text": "Python", "origin": "user", "source_refs": []}
                    ],
                },
            ],
            "metadata": {"template_id": "00000000-0000-4000-8000-000000000101"},
        }
    )
    source = render(example).pdf if kind == "pdf" else export_docx(example)
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        created = client.post(
            "/api/imports",
            json={
                "filename": "resume." + kind,
                "mime": "application/pdf"
                if kind == "pdf"
                else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "content_base64": base64.b64encode(source).decode(),
            },
        )
        assert created.status_code == 201, created.text
        run = created.json()
        data = [
            (
                "experience",
                {
                    "type": "experience",
                    "company": "Orbit Ltd",
                    "job_title": "API Developer",
                    "start_date": "2020-01-01",
                },
                "Orbit Ltd",
            ),
            (
                "achievement",
                {
                    "type": "achievement",
                    "experience_id": "@experience",
                    "text": "Built Python APIs and reduced latency by 40%.",
                    "metric_value": "40",
                    "metric_unit": "%",
                },
                "40%",
            ),
            (
                "project",
                {"type": "project", "name": "Orbit project", "description": "Built Python APIs."},
                "Orbit project",
            ),
            (
                "education",
                {
                    "type": "education",
                    "institution": "Example University",
                    "degree": "Bachelor",
                    "field": "Computer Science",
                },
                "Example University",
            ),
            ("skill", {"type": "skill", "name": "Python"}, "Python"),
        ]
        candidates = []
        for key, fields, quote in data:
            fragment = next(f for f in run["fragments"] if quote in f["text"])
            candidates.append(
                {
                    "key": key,
                    "data": fields,
                    "locator": fragment["locator"],
                    "excerpt": quote,
                    "decision": "accepted",
                    "user_supplied": True,
                }
            )
        reviewed = client.put(
            f"/api/imports/{run['id']}", json={"expected_revision": 1, "candidates": candidates}
        )
        assert reviewed.status_code == 200, reviewed.text
        committed = client.post(f"/api/imports/{run['id']}/commit?revision=2")
        assert committed.status_code == 200, committed.text
        ids = dict(zip([item[0] for item in data], committed.json()["saved_ids"], strict=True))
        for section, key in zip(
            example.sections, ["achievement", "project", "education", "skill"], strict=True
        ):
            section.items[0].source_refs = [
                SourceRef.model_validate({"entity_type": key, "entity_id": ids[key]})
            ]
        saved = client.post(
            "/api/resumes",
            json={"title": "Imported master", "content": example.model_dump(mode="json")},
        )
        assert saved.status_code == 201, saved.text
        assert client.get(f"/api/resumes/{saved.json()['id']}/pdf").content.startswith(b"%PDF")


def test_parse_cancel_blocks_late_results_and_restart_marks_failure(database_url, monkeypatch):
    started, released = Event(), Event()

    def held_parser(*args):
        started.set()
        assert released.wait(10)
        return [Fragment(locator="paragraph 1", text="Synthetic")]

    monkeypatch.setattr("app.importers.service.parse", held_parser)
    app = create_app(Settings(database_url=database_url))
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            client.post,
            "/api/imports",
            json={
                "filename": "held.docx",
                "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "content_base64": base64.b64encode(docx("Synthetic")).decode(),
            },
        )
        assert started.wait(10)
        run = client.get("/api/imports").json()[0]
        assert run["status"] == "parsing"
        assert client.post(f"/api/imports/{run['id']}/cancel").status_code == 204
        released.set()
        assert future.result(timeout=10).status_code == 409
        failed = client.get(f"/api/imports/{run['id']}").json()
        assert failed["status"] == "failed" and failed["fragments"] == []
        assert client.get("/api/career/project").json() == []
        with Session(app.state.engine) as db:
            interrupted = imports.create(
                db,
                LOCAL_OWNER,
                "interrupted.docx",
                "application/pdf",
                {"fragments": [], "candidates": [], "saved_ids": []},
                None,
            )
    with TestClient(create_app(Settings(database_url=database_url))) as restarted:
        assert restarted.get(f"/api/imports/{interrupted.id}").json()["status"] == "failed"
