import copy
import json
import zipfile
from io import BytesIO
from uuid import uuid4
from xml.etree import ElementTree

import httpx
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.core.config import Settings
from app.main import create_app
from app.rendering.docx import W, export
from app.resumes.schemas import ResumeDocument


@pytest.mark.parametrize("template", ["classic", "modern"])
def test_experience_summary_duties_exports_and_immutable_facts(
    database_url: str, template: str
) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        source = {
            "type": "experience",
            "company": "Example Company",
            "job_title": "Engineer",
            "start_date": "2020-01-01",
            "current": True,
            "description": "Built reliable systems.\nMaintained APIs\nReviewed changes",
        }
        record = client.post("/api/career", json=source).json()
        template_id = next(
            t["id"]
            for t in client.get("/api/resumes/templates").json()
            if t["builtin_key"] == template
        )
        content = {
            "schema_version": 1,
            "header": {"name": "Synthetic Candidate"},
            "metadata": {"template_id": template_id},
            "sections": [
                {
                    "key": str(uuid4()),
                    "type": "experience",
                    "title": "Experience",
                    "items": [
                        {
                            "key": str(uuid4()),
                            "text": text,
                            "origin": "user",
                            "experience_summary": index == 0,
                            "source_refs": [
                                {"entity_type": "experience", "entity_id": record["id"]}
                            ],
                        }
                        for index, text in enumerate(
                            ["Built reliable systems.", "Maintained APIs", "Reviewed changes"]
                        )
                    ],
                }
            ],
        }
        response = client.post(
            "/api/resumes", json={"title": "Structured master", "content": content}
        )
        assert response.status_code == 201, response.text
        saved = response.json()
        preview = client.post("/api/resumes/preview", json=saved["content"])
        assert preview.status_code == 200, preview.text
        assert "<p class='text'>Built reliable systems.</p>" in preview.json()["html"]
        assert "<p class='bullet'>Maintained APIs</p>" in preview.json()["html"]
        pdf = client.get(f"/api/resumes/{saved['id']}/pdf")
        text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf.content)).pages)
        for value in [
            "Example Company",
            "Engineer",
            "2020-01-01",
            "Present",
            "Built reliable systems.",
            "Maintained APIs",
            "Reviewed changes",
        ]:
            assert value in text
        with zipfile.ZipFile(
            BytesIO(export(ResumeDocument.model_validate(saved["content"])))
        ) as bundle:
            root = ElementTree.fromstring(bundle.read("word/document.xml"))
        paragraphs = root.findall(f".//{{{W}}}p")
        for value, bullet in [
            ("Built reliable systems.", False),
            ("Maintained APIs", True),
            ("Reviewed changes", True),
        ]:
            paragraph = next(p for p in paragraphs if "".join(p.itertext()) == value)
            assert (paragraph.find(f".//{{{W}}}numPr") is not None) == bullet
        changed = {
            **source,
            "company": "Updated Company",
            "current": False,
            "end_date": "2024-01-01",
        }
        assert client.put(f"/api/career/{record['id']}", json=changed).status_code == 200
        response = client.put(
            f"/api/resumes/{saved['id']}",
            json={"title": saved["title"], "content": saved["content"], "expected_version": 1},
        )
        assert response.status_code == 200, response.text
        assert (
            response.json()["content"]["sections"][0]["items"][0]["facts"]["employer"]
            == "Updated Company"
        )
        history = client.get(f"/api/resumes/{saved['id']}/versions").json()
        # History ordering is intentionally independent of the immutability assertion.
        original = next(v for v in history if v["version_number"] == 1)
        assert (
            original["content"]["sections"][0]["items"][0]["facts"]["employer"] == "Example Company"
        )
        invalid = copy.deepcopy(content)
        invalid["sections"][0]["items"][0]["text"] = "First sentence. Another sentence."
        assert (
            client.post("/api/resumes", json={"title": "Invalid", "content": invalid}).status_code
            == 422
        )
        invalid["sections"][0]["items"][0]["text"] = "One sentence."
        invalid["sections"][0]["type"] = "summary"
        assert (
            client.post("/api/resumes", json={"title": "Invalid", "content": invalid}).status_code
            == 422
        )


def test_old_experience_items_default_to_duties() -> None:
    from test_phase1 import document

    content = document("00000000-0000-4000-8000-000000000101", {"id": str(uuid4())})
    parsed = ResumeDocument.model_validate(content)
    assert parsed.sections[0].items[0].experience_summary is False


@pytest.mark.parametrize("multiple_sentences", [False, True])
def test_generation_preserves_summary_role_and_rejects_multiple_sentences(
    database_url: str, multiple_sentences: bool
) -> None:
    from test_phase2 import sse
    from test_phase3 import generate, install, setup, transport

    with TestClient(create_app(Settings(database_url=database_url))) as client:
        master, job = setup(client)
        master["content"]["sections"][0]["items"][0]["experience_summary"] = True
        response = client.put(
            f"/api/resumes/{master['id']}",
            json={"title": master["title"], "content": master["content"], "expected_version": 1},
        )
        assert response.status_code == 200, response.text
        baseline = transport()

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            if (
                multiple_sentences
                and payload["response_format"]["json_schema"]["name"] == "Rewrite"
            ):
                context = json.loads(payload["messages"][1]["content"].split("DATA:\n")[1])
                return sse(
                    {
                        "text": "Built Python APIs. Reduced latency by 40%.",
                        "source_ids": list(context["sources"]),
                    }
                )
            return baseline.handle_request(request)

        install(client, httpx.MockTransport(handler))
        run = generate(client, response.json(), job)
        assert run["status"] == "succeeded", run
        assert run["proposed"]["sections"][0]["items"][0]["experience_summary"] is True
        suggestion = run["suggestions"][0]
        if multiple_sentences:
            assert suggestion["verification"] == "unsupported"
            assert suggestion["proposed"] is None
            assert "one sentence" in suggestion["reason"]
        else:
            assert suggestion["proposed"]["experience_summary"] is True
            assert suggestion["verification"] == "supported"
            decision = {
                "decisions": [{"suggestion_id": suggestion["id"], "action": "accept"}],
                "expected_revision": 0,
            }
            saved = client.post(
                f"/api/generation/{run['id']}/commit",
                json={**decision, "title": "Tailored summary"},
            )
            assert saved.status_code == 201, saved.text
            assert saved.json()["content"]["sections"][0]["items"][0]["experience_summary"] is True
