from fastapi.testclient import TestClient
from test_phase1 import document

from app.core.config import Settings
from app.main import create_app


def test_one_gold_standard_and_stale_save_rolls_back(database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        template = client.get("/api/resumes/templates").json()[0]["id"]
        content = document(template)
        first = client.post(
            "/api/resumes", json={"title": "First", "content": content, "gold_standard": True}
        ).json()
        second = client.post(
            "/api/resumes", json={"title": "Second", "content": content, "gold_standard": True}
        ).json()
        masters = client.get("/api/resumes").json()
        assert [master["id"] for master in masters if master["gold_standard"]] == [second["id"]]
        stale = client.put(
            f"/api/resumes/{first['id']}",
            json={
                "title": "Stale",
                "content": content,
                "gold_standard": True,
                "expected_version": 99,
            },
        )
        assert stale.status_code == 409
        masters = client.get("/api/resumes").json()
        assert [master["id"] for master in masters if master["gold_standard"]] == [second["id"]]
        assert client.get(f"/api/resumes/{first['id']}").json()["title"] == "First"
