import base64
import io
import struct
import zipfile
import zlib
from xml.etree import ElementTree as ET

import pytest
from fastapi.testclient import TestClient
from test_phase3 import setup

from app.core.config import Settings
from app.main import create_app


def png() -> bytes:
    def chunk(name, data):
        return (
            struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00\x24\x36\x2e"))
        + chunk(b"IEND", b"")
    )


def test_docx_content_semantics_and_historical_export(database_url):
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        master, _ = setup(client)
        version = client.get(f"/api/resumes/{master['id']}/versions").json()[0]
        response = client.get(f"/api/resumes/versions/{version['id']}/docx")
        assert response.status_code == 200, response.text
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            for name in archive.namelist():
                if name.endswith((".xml", ".rels")):
                    ET.fromstring(archive.read(name))
            content = archive.read("word/document.xml").decode()
            assert "Synthetic Candidate" in content and "40%" in content
            assert "Stored Employer" in content and "Stored Title" in content
            assert "2020-01-01" in content
            assert "w:numPr" in content and "Heading1" in content
            assert version["id"] not in content and "source_refs" not in content
            assert "word/fonts/resume.odttf" in archive.namelist()
            assert not any("vba" in n.lower() for n in archive.namelist())
        ref = master["content"]["sections"][0]["items"][0]["source_refs"][0]
        client.delete(f"/api/career/{ref['entity_type']}/{ref['entity_id']}")
        assert client.get(f"/api/resumes/versions/{version['id']}/docx").status_code == 200
        assert client.get(f"/api/resumes/versions/{version['id']}").json() == version


@pytest.mark.parametrize(
    "html,css",
    [
        ("<script>alert(1)</script>{{header}}{{sections}}", ""),
        ('<div onclick="alert(1)">{{header}}{{sections}}</div>', ""),
        ('<img src="https://evil.example" alt="x">{{header}}{{sections}}', ""),
        ("{{header}}{{sections}}{{unknown}}", ""),
        ("{{header}}{{sections}}", '@import "https://evil.example";'),
        ("{{header}}{{sections}}", "p{background-image:url(file:///secret)}"),
        ("{{header}}{{sections}}", "p{font-size:2pt}"),
        ("{{header}}{{sections}}", "p{position:absolute}"),
    ],
)
def test_custom_templates_reject_unsafe_input(database_url, html, css):
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        assert (
            client.post(
                "/api/templates", json={"name": "Unsafe", "html": html, "css": css}
            ).status_code
            == 422
        )
        assert client.get("/api/templates").json() == []


def test_template_revision_retirement_asset_and_source_snapshot(database_url, monkeypatch):
    monkeypatch.setenv("APP_UPLOAD_KEY", base64.b64encode(b"a" * 32).decode())
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        asset_response = client.post(
            "/api/templates/assets", json={"content_base64": base64.b64encode(png()).decode()}
        )
        assert asset_response.status_code == 201, asset_response.text
        asset = asset_response.json()
        body = {
            "name": "Private custom",
            "html": '<header><img src="asset:'
            + asset["id"]
            + '" alt="Decorative mark">{{header}}</header>{{sections}}',
            "css": "h1{color:#24362e}",
            "asset_ids": [asset["id"]],
        }
        first = client.post("/api/templates", json=body).json()
        master, _ = setup(client)
        content = master["content"]
        content["metadata"]["template_id"] = first["id"]
        saved = client.post(
            "/api/resumes", json={"title": "Custom sourced master", "content": content}
        )
        assert saved.status_code == 201, saved.text
        version = client.get(f"/api/resumes/{saved.json()['id']}/versions").json()[0]
        pdf_before = client.get(f"/api/resumes/versions/{version['id']}/pdf")
        assert pdf_before.status_code == 200, pdf_before.text
        changed = client.put(
            f"/api/templates/{first['document_id']}",
            json={
                **body,
                "name": "Changed custom",
                "css": "h1{color:#345678}",
                "expected_revision": 1,
            },
        )
        assert changed.status_code == 200 and changed.json()["revision"] == 2
        assert client.delete(f"/api/templates/{first['id']}").status_code == 204
        assert (
            client.get(f"/api/resumes/versions/{version['id']}/pdf").content == pdf_before.content
        )
        assert client.get(f"/api/resumes/versions/{version['id']}/docx").status_code == 422
        assert (
            client.post(
                "/api/resumes", json={"title": "Retired template", "content": content}
            ).status_code
            == 422
        )
        exported = client.get("/api/privacy/export").json()
        assert (
            exported["tables"]["template_assets"][0]["ciphertext"]
            != base64.b64encode(png()).decode()
        )


def test_template_asset_missing_key_and_invalid_png(database_url, monkeypatch):
    monkeypatch.delenv("APP_UPLOAD_KEY", raising=False)
    monkeypatch.delenv("APP_ENCRYPTION_KEY", raising=False)
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        assert (
            client.post(
                "/api/templates/assets", json={"content_base64": base64.b64encode(png()).decode()}
            ).status_code
            == 503
        )
        assert (
            client.post(
                "/api/templates/assets",
                json={"content_base64": base64.b64encode(b"<svg onload='bad'>").decode()},
            ).status_code
            == 422
        )


def test_template_save_measures_reading_order_before_use(database_url):
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        saved = client.post(
            "/api/templates", json={"name": "Reordered", "html": "{{sections}}{{header}}"}
        )
        assert saved.status_code == 201, saved.text
        assert any("reading order" in finding for finding in saved.json()["snapshot"]["findings"])
