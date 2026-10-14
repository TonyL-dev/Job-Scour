import json
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from test_phase2 import ANALYSIS, sse
from test_phase3 import install, setup, transport

from app.core.config import Settings
from app.main import create_app


def test_cover_letter_review_history_and_exact_application_link(database_url):
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        master, job = setup(client)
        install(client, transport())
        analysis = client.post(
            f"/api/jobs/{job['id']}/analyze", json={"use_embeddings": False}
        ).json()
        profile = client.get("/api/settings").json()["profiles"][0]["id"]
        client.put(
            "/api/settings/assignments", json={"task": "cover_letter", "profile_id": profile}
        )
        ref = master["content"]["sections"][0]["items"][0]["source_refs"][0]

        def handler(request):
            payload = json.loads(request.content)
            schema = payload["response_format"]["json_schema"]["name"]
            if schema == "JobAnalysis":
                return sse(ANALYSIS)
            if schema == "Paragraphs":
                return sse(
                    {
                        "paragraphs": [
                            {
                                "key": str(uuid4()),
                                "text": "Reduced latency by 40% using Python APIs.",
                                "origin": "ai",
                                "source_refs": [ref],
                            }
                        ]
                    }
                )
            assert schema == "Verification"
            return sse({"status": "supported", "reason": "Supported by selected achievement"})

        install(client, httpx.MockTransport(handler))
        run = client.post(
            "/api/letters/runs",
            json={
                "title": "Synthetic cover letter",
                "job_id": job["id"],
                "analysis_id": analysis["id"],
                "sources": [ref],
                "content": {"author": {"name": "Synthetic Candidate"}},
            },
        ).json()
        generated = client.post(f"/api/letters/runs/{run['id']}/execute?revision=1")
        assert generated.status_code == 200, generated.text
        review = generated.json()
        assert review["status"] == "review", review
        commit_body = {
            "expected_revision": review["revision"],
            "title": "Synthetic cover letter",
            "content": review["proposed"],
        }
        response = client.post(f"/api/letters/runs/{run['id']}/commit", json=commit_body)
        assert response.status_code == 200, response.text
        version = response.json()
        assert (
            client.post(f"/api/letters/runs/{run['id']}/commit", json=commit_body).json() == version
        )
        assert client.get(f"/api/letters/versions/{version['id']}/pdf").content.startswith(b"%PDF")
        revised = json.loads(json.dumps(version["content"]))
        revised["paragraphs"][0].update(
            origin="user", text="Built Python APIs and reduced latency by 40%."
        )
        edited = client.put(
            f"/api/letters/versions/{version['id']}",
            json={"expected_version": 1, "content": revised},
        )
        assert edited.status_code == 200, edited.text
        assert edited.json()["version_number"] == 2
        resume_version = client.get(f"/api/resumes/{master['id']}/versions").json()[0]
        application = client.post(
            "/api/applications",
            json={
                "company": "Synthetic",
                "position": "Developer",
                "version_id": resume_version["id"],
                "job_id": job["id"],
                "cover_letter_version_id": version["id"],
            },
        )
        assert application.status_code == 201, application.text
        assert application.json()["cover_letter_version_id"] == version["id"]
        assert client.get(f"/api/letters/versions/{version['id']}").json() == version
        client.delete(f"/api/career/{ref['entity_type']}/{ref['entity_id']}")
        assert client.get(f"/api/letters/versions/{version['id']}/pdf").content.startswith(b"%PDF")
        restored = client.post(f"/api/letters/versions/{version['id']}/restore?expected_version=2")
        assert restored.status_code == 200 and restored.json()["version_number"] == 3


def test_cover_letter_unsupported_claim_cannot_be_accepted(database_url):
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        master, job = setup(client)
        install(client, transport())
        analysis = client.post(
            f"/api/jobs/{job['id']}/analyze", json={"use_embeddings": False}
        ).json()
        profile = client.get("/api/settings").json()["profiles"][0]["id"]
        client.put(
            "/api/settings/assignments", json={"task": "cover_letter", "profile_id": profile}
        )
        ref = master["content"]["sections"][0]["items"][0]["source_refs"][0]
        install(
            client,
            httpx.MockTransport(
                lambda request: sse(
                    {
                        "paragraphs": [
                            {
                                "key": str(uuid4()),
                                "text": "Reduced latency by 400% using Kubernetes.",
                                "origin": "ai",
                                "source_refs": [ref],
                            }
                        ]
                    }
                )
            ),
        )
        run = client.post(
            "/api/letters/runs",
            json={
                "title": "Rejected letter",
                "job_id": job["id"],
                "analysis_id": analysis["id"],
                "sources": [ref],
                "content": {"author": {"name": "Synthetic"}},
            },
        ).json()
        review = client.post(f"/api/letters/runs/{run['id']}/execute?revision=1").json()
        assert set(review["support"].values()) == {"unsupported"}
        commit = client.post(
            f"/api/letters/runs/{run['id']}/commit",
            json={
                "expected_revision": review["revision"],
                "title": "Bad letter",
                "content": review["proposed"],
            },
        )
        assert commit.status_code == 422
        assert client.get("/api/letters/versions").json() == []
