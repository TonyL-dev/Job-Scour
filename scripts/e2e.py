"""Real Playwright workflows A/D/E/F with synthetic model responses and SQLCipher storage.

This launches isolated services and never reads the normal career database or calls a model.
"""

import base64
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait(url: str) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(0.2)
    raise RuntimeError("Fixture service did not become ready: " + url)


def stop(process: subprocess.Popen) -> None:
    if process.poll() is None:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
        else:
            import signal

            os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=15)


def main() -> None:
    evidence = ROOT / ".validation"
    evidence.mkdir(exist_ok=True)
    api_port, web_port = port(), port()
    url = f"http://127.0.0.1:{web_port}"
    pnpm = shutil.which("pnpm") or shutil.which("pnpm.cmd")
    if not pnpm:
        raise SystemExit("pnpm 11.19.0 must be on PATH")
    services: list[subprocess.Popen] = []
    env = dict(os.environ)
    env.pop("APP_ENCRYPTION_KEY", None)
    env.update(
        APP_MODE="local",
        PYTHONUTF8="1",
        E2E_BACKEND_PORT=str(api_port),
        API_PROXY_TARGET=f"http://127.0.0.1:{api_port}",
        APP_DATABASE_PASSPHRASE="synthetic browser passphrase",
        APP_UPLOAD_KEY=base64.b64encode(b"synthetic-upload-key-32-bytes!!!!"[:32]).decode(),
        APP_FRONTEND_ORIGINS=json.dumps([url]),
    )
    with tempfile.TemporaryDirectory(prefix="phase4-e2e-", dir=evidence) as temporary:
        env["APP_DATABASE_URL"] = f"sqlite:///{Path(temporary) / 'encrypted.db'}"
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND,
            env=env,
            check=True,
        )
        with (
            (evidence / "phase4-e2e-backend.log").open("w", encoding="utf-8") as log,
            (evidence / "phase4-e2e-frontend.log").open("w", encoding="utf-8") as web_log,
        ):
            options = (
                {"creationflags": subprocess.CREATE_NO_WINDOW}
                if os.name == "nt"
                else {"start_new_session": True}
            )
            try:
                services.append(
                    subprocess.Popen(
                        [sys.executable, "tests/e2e_server.py"],
                        cwd=BACKEND,
                        env=env,
                        stdout=log,
                        stderr=log,
                        **options,
                    )
                )
                services.append(
                    subprocess.Popen(
                        [pnpm, "dev", "--port", str(web_port)],
                        cwd=ROOT / "frontend",
                        env=env,
                        stdout=web_log,
                        stderr=web_log,
                        **options,
                    )
                )
                wait(url + "/api/health")
                errors: list[str] = []
                external: list[str] = []
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch()
                    page = browser.new_page(viewport={"width": 1440, "height": 1000})
                    page.set_default_timeout(30000)
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on(
                        "request",
                        lambda request: (
                            external.append(request.url)
                            if not request.url.startswith(url)
                            else None
                        ),
                    )
                    try:
                        # Phase 6A: real DOCX parser -> staged manual review -> career records.
                        imported = io.BytesIO()
                        with zipfile.ZipFile(imported, "w") as document:
                            document.writestr(
                                "word/document.xml",
                                '<w:document xmlns:w="http://schemas.openxmlformats.org/'
                                'wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>'
                                "Orbit project reduced latency by 40%"
                                "</w:t></w:r></w:p></w:body></w:document>",
                            )
                        page.goto(url + "/imports")
                        page.get_by_label("Resume file", exact=True).set_input_files(
                            {
                                "name": "synthetic.docx",
                                "mimeType": "application/vnd.openxmlformats-officedocument."
                                "wordprocessingml.document",
                                "buffer": imported.getvalue(),
                            }
                        )
                        page.get_by_role("button", name="Parse locally", exact=True).click()
                        expect(
                            page.get_by_role("heading", name="Review synthetic.docx")
                        ).to_be_visible()
                        page.get_by_role("button", name="Add candidate manually").click()
                        page.get_by_label("Name (required)", exact=True).fill("Orbit")
                        page.get_by_label("Description", exact=True).fill("Latency project")
                        page.get_by_label("Decision", exact=True).select_option("accepted")
                        page.get_by_role("button", name="Commit approved facts").click()
                        expect(
                            page.get_by_text("1 approved records saved.", exact=False)
                        ).to_be_visible()
                        page.reload()
                        expect(
                            page.get_by_role("button", name="synthetic.docx · committed")
                        ).to_be_visible()
                        page.screenshot(
                            path=str(evidence / "phase6-import-browser.png"),
                            full_page=True,
                        )
                        # A: configuration/privacy and a manually entered career record.
                        page.goto(url)
                        expect(page.get_by_text("Backend connected", exact=False)).to_be_visible()
                        page.get_by_role("link", name="AI settings", exact=True).click()
                        expect(page.get_by_label("Rewriting model", exact=True)).not_to_have_value(
                            ""
                        )
                        page.goto(url + "/career/skill")
                        page.get_by_role("button", name="Add record", exact=True).click()
                        page.get_by_label("Name *", exact=True).fill("Python")
                        page.get_by_label("Category", exact=True).select_option("language")
                        page.get_by_role("button", name="Save record", exact=True).click()
                        expect(page.get_by_text("Career record saved.", exact=True)).to_be_visible()
                        # D: real pipeline/review/PDF with a synthetic provider.
                        page.get_by_role("link", name="Generate & review", exact=True).click()
                        page.get_by_label("Generation master", exact=True).select_option(
                            label="Synthetic master"
                        )
                        page.get_by_label("Generation job", exact=True).select_option(index=1)
                        page.get_by_role("button", name="Generate suggestions", exact=True).click()
                        expect(
                            page.get_by_role("heading", name="Review changes", exact=True)
                        ).to_be_visible(timeout=60000)
                        page.get_by_role(
                            "button", name="Accept all supported changes", exact=True
                        ).click()
                        expect(page.locator(".pdf-pages canvas").first).to_be_visible()
                        page.get_by_role("button", name="Save tailored resume", exact=True).click()
                        expect(
                            page.get_by_text("Tailored resume saved: Tailored resume", exact=True)
                        ).to_be_visible()
                        page.get_by_role(
                            "link",
                            name="ATS checks, history & track application →",
                            exact=True,
                        ).click()
                        expect(
                            page.get_by_role("heading", name="ATS guidance", exact=True)
                        ).to_be_visible()
                        page.get_by_label("Job analysis (optional)", exact=True).select_option(
                            "auto"
                        )
                        page.get_by_role(
                            "button", name="Run ATS checks on this PDF", exact=True
                        ).click()
                        expect(
                            page.get_by_text(
                                "Deterministic guidance, not a real ATS vendor verdict.",
                                exact=True,
                            )
                        ).to_be_visible()
                        expect(page.get_by_text("keywords:", exact=False)).to_be_visible()
                        page.screenshot(
                            path=str(evidence / "phase4-history-desktop.png"),
                            full_page=True,
                        )
                        # F: exact-version tracking, stage events, persisted notes, PDF download.
                        page.get_by_role(
                            "link", name="Track this application →", exact=True
                        ).click()
                        page.get_by_label("Company", exact=True).fill("Synthetic Company")
                        page.get_by_label("Position", exact=True).fill("API Developer")
                        page.get_by_label("Notes", exact=True).fill("Synthetic browser notes")
                        page.get_by_role("button", name="Save application", exact=True).click()
                        expect(page.get_by_text("Application saved.", exact=True)).to_be_visible()
                        page.get_by_label("Stage", exact=True).select_option("interview")
                        page.get_by_role("button", name="Record stage event", exact=True).click()
                        expect(
                            page.get_by_text("Stage event recorded.", exact=True)
                        ).to_be_visible()
                        with page.expect_download() as download:
                            page.get_by_role("button", name="Submitted PDF", exact=True).click()
                        download.value.save_as(str(evidence / "phase4-submitted.pdf"))
                        page.reload()
                        expect(
                            page.get_by_role(
                                "button",
                                name="Synthetic Company · API Developer",
                                exact=True,
                            )
                        ).to_be_visible()
                        page.set_viewport_size({"width": 390, "height": 844})
                        page.screenshot(
                            path=str(evidence / "phase4-tracker-mobile.png"),
                            full_page=True,
                        )
                        assert not page.evaluate(
                            "document.documentElement.scrollWidth > innerWidth"
                        ), "Mobile overflow"
                        page.set_viewport_size({"width": 1440, "height": 1000})
                        # E: autosave, immutable history, compare, restore, duplicate and old PDF.
                        page.goto(url + "/resumes")
                        page.get_by_label("Saved resumes", exact=True).select_option(
                            label="Synthetic master"
                        )
                        page.get_by_label("Full name *", exact=True).fill(
                            "Synthetic Candidate Edited"
                        )
                        expect(page.get_by_text("Saved · version 2", exact=True)).to_be_visible(
                            timeout=15000
                        )
                        page.get_by_role(
                            "link", name="History & ATS guidance →", exact=True
                        ).click()
                        page.get_by_label("Version", exact=True).select_option(index=1)
                        page.get_by_label("Compare with", exact=True).select_option(index=1)
                        page.get_by_role(
                            "button", name="Restore as new version", exact=True
                        ).click()
                        expect(
                            page.get_by_text("Restored as a new version.", exact=True)
                        ).to_be_visible()
                        page.get_by_role("button", name="Duplicate", exact=True).click()
                        expect(
                            page.get_by_text("Separate copy created.", exact=True)
                        ).to_be_visible()
                        # Phase 6B: AI questions, explicit user answers and confirmation.
                        page.goto(url + "/profile")
                        page.get_by_label("Career evidence", exact=True).select_option(
                            label="Orbit"
                        )
                        page.get_by_role("button", name="Ask follow-up questions").click()
                        page.get_by_label("Answer 1", exact=True).fill("Reduced latency by 40%")
                        page.get_by_label("Answer 2", exact=True).fill("unknown")
                        page.get_by_role("button", name="Prepare factual edit").click()
                        expect(page.get_by_label("Proposed wording", exact=True)).to_contain_text(
                            "40%"
                        )
                        page.get_by_role("button", name="Confirm my factual edit").click()
                        expect(page.get_by_role("button", name="Orbit · confirmed")).to_be_visible()
                        # Phase 6C/E: supported letter review, actual PDF and DOCX export.
                        page.goto(url + "/letters")
                        page.get_by_label("Saved job analysis", exact=True).select_option(index=1)
                        page.get_by_label("Your name", exact=True).fill("Synthetic Candidate")
                        page.get_by_label(
                            "Built Python APIs and reduced latency by 40%.", exact=True
                        ).check()
                        page.get_by_role("button", name="Generate letter paragraphs").click()
                        expect(page.get_by_label("Keep paragraph", exact=True)).to_be_enabled()
                        page.get_by_role("button", name="Save reviewed letter").click()
                        expect(page.get_by_text("Cover letter saved.", exact=True)).to_be_visible()
                        expect(page.locator(".pdf-pages canvas").first).to_be_visible()
                        with page.expect_download() as downloaded_letter:
                            page.get_by_role(
                                "button", name="Download letter DOCX", exact=True
                            ).click()
                        downloaded_letter.value.save_as(str(evidence / "phase6-letter.docx"))
                        page.screenshot(
                            path=str(evidence / "phase6-letter-browser.png"),
                            full_page=True,
                        )
                        # Phase 6D: synthetic comparison and explicit activation/rollback.
                        page.goto(url + "/prompts")
                        page.get_by_label("Prompt name", exact=True).fill(
                            "Synthetic baseline preference"
                        )
                        page.get_by_role("button", name="Save new preference version").click()
                        page.get_by_role("button", name="Evaluate baseline & candidate").click()
                        expect(
                            page.get_by_role("heading", name="Applicable synthetic checks passed")
                        ).to_be_visible(timeout=60000)
                        page.get_by_role("button", name="Activate this evaluated version").click()
                        expect(
                            page.get_by_text(
                                "Prompt activated for new calls. "
                                "Existing runs retain their captured version.",
                                exact=True,
                            )
                        ).to_be_visible()
                        # Phase 6F: actual custom-template PDF and immutable revision save.
                        page.goto(url + "/templates")
                        page.get_by_label("Template name", exact=True).fill(
                            "Synthetic custom template"
                        )
                        page.get_by_role("button", name="Validate & preview synthetic PDF").click()
                        expect(page.locator(".pdf-pages canvas").first).to_be_visible()
                        page.get_by_role(
                            "button", name="Save template revision", exact=True
                        ).click()
                        expect(
                            page.get_by_text("Immutable template revision saved.", exact=True)
                        ).to_be_visible()
                        page.screenshot(
                            path=str(evidence / "phase6-template-browser.png"),
                            full_page=True,
                        )
                        page.goto(url + "/history")
                        page.get_by_label("Resume history document", exact=True).select_option(
                            index=1
                        )
                        with page.expect_download() as downloaded_resume:
                            page.get_by_role(
                                "button", name="Download selected version DOCX"
                            ).click()
                        downloaded_resume.value.save_as(str(evidence / "phase6-resume.docx"))
                        # Structured master experience: real source save, PDF.js and reload.
                        page.goto(url + "/resumes")
                        page.get_by_label("Resume title", exact=True).fill(
                            "Structured experience master"
                        )
                        page.get_by_label("Full name *", exact=True).fill(
                            "Synthetic Experience Candidate"
                        )
                        page.get_by_label("New section", exact=True).select_option("experience")
                        page.get_by_role("button", name="Add section", exact=True).click()
                        page.get_by_role("button", name="Add experience", exact=True).click()
                        form = page.get_by_role("form", name="Add experience", exact=True)
                        form.get_by_label("Company *", exact=True).fill("Structured Company")
                        form.get_by_label("Title *", exact=True).fill("Systems Engineer")
                        form.get_by_label("Start date *", exact=True).fill("2021-01-01")
                        form.get_by_label("Present", exact=True).check()
                        form.get_by_label("Summary (one sentence max)", exact=True).fill(
                            "Built reliable systems."
                        )
                        form.get_by_label("Duty 1", exact=True).fill("Maintained APIs")
                        form.get_by_role("button", name="Add duty", exact=True).click()
                        form.get_by_label("Duty 2", exact=True).fill("Reviewed changes")
                        form.get_by_role(
                            "button", name="Add experience to draft", exact=True
                        ).click()
                        expect(
                            page.get_by_text(
                                "Experience saved to the career library and added to this draft.",
                                exact=True,
                            )
                        ).to_be_visible()
                        page.get_by_role("button", name="Save master", exact=True).click()
                        expect(page.get_by_text("Saved · version 1", exact=True)).to_be_visible()
                        expect(page.locator(".pdf-pages canvas").first).to_be_visible()
                        page.get_by_label("Preview format", exact=True).select_option("html")
                        frame = page.frame_locator('iframe[title="Resume HTML preview"]')
                        expect(
                            frame.locator("p.text", has_text="Built reliable systems.")
                        ).to_be_visible()
                        expect(frame.locator("p.bullet")).to_have_count(2)
                        page.get_by_role(
                            "button",
                            name="Edit details: Systems Engineer · Structured Company",
                            exact=True,
                        ).click()
                        edit = page.get_by_role("form", name="Edit experience details", exact=True)
                        edit.get_by_label("Present", exact=True).uncheck()
                        edit.get_by_label("End date", exact=True).fill("2025-12-31")
                        edit.get_by_role(
                            "button", name="Save experience details", exact=True
                        ).click()
                        expect(page.get_by_text("Saved · version 2", exact=True)).to_be_visible(
                            timeout=15000
                        )
                        expect(frame.locator("p.facts")).to_contain_text("2025-12-31")
                        page.reload()
                        page.get_by_label("Saved resumes", exact=True).select_option(
                            label="Structured experience master"
                        )
                        expect(
                            page.get_by_role(
                                "textbox", name="Summary (one sentence max)", exact=True
                            )
                        ).to_have_value("Built reliable systems.", timeout=15000)
                        expect(
                            page.get_by_role("textbox", name="Duty (bullet point)", exact=True)
                        ).to_have_count(2)
                        expect(page.locator(".pdf-pages canvas").first).to_be_visible()
                        page.screenshot(
                            path=str(evidence / "structured-experience-browser.png"),
                            full_page=True,
                        )
                        # Privacy: actual cookies, unlock, JSON/PDF archive and delete-all.
                        page.get_by_role("link", name="Privacy", exact=True).click()
                        expect(
                            page.get_by_text(
                                "Full SQLite database encryption enabled (SQLCipher).",
                                exact=True,
                            )
                        ).to_be_visible()
                        page.get_by_label("New passcode", exact=True).fill(
                            "synthetic lock passcode"
                        )
                        page.get_by_role("button", name="Set passcode", exact=True).click()
                        expect(page.get_by_text("Passcode saved.", exact=True)).to_be_visible()
                        page.get_by_role("button", name="Lock workspace", exact=True).click()
                        expect(
                            page.get_by_role("heading", name="Workspace locked", exact=True)
                        ).to_be_visible()
                        page.reload()
                        expect(
                            page.get_by_role("heading", name="Workspace locked", exact=True)
                        ).to_be_visible()
                        page.get_by_label("Passcode", exact=True).fill("synthetic lock passcode")
                        page.get_by_role("button", name="Unlock workspace", exact=True).click()
                        expect(
                            page.get_by_role("heading", name="Privacy controls.", exact=True)
                        ).to_be_visible()
                        with page.expect_download() as archive:
                            page.get_by_role(
                                "button",
                                name="Export JSON + all PDFs (ZIP)",
                                exact=True,
                            ).click()
                        archive.value.save_as(str(evidence / "phase4-export.zip"))
                        page.get_by_label("Type DELETE ALL MY DATA", exact=True).fill(
                            "DELETE ALL MY DATA"
                        )
                        page.get_by_role(
                            "button", name="Delete all workspace data", exact=True
                        ).click()
                        expect(
                            page.get_by_text(
                                "Workspace data deleted. Passcode retained.", exact=True
                            )
                        ).to_be_visible()
                        response = page.request.get(url + "/api/privacy/export")
                        assert all(not rows for rows in response.json()["tables"].values())
                        assert not errors and not external, (errors, external)
                        (evidence / "phase6-browser-evidence.json").write_text(
                            json.dumps(
                                {
                                    "passed": True,
                                    "flows": [
                                        "A",
                                        "D",
                                        "E",
                                        "F",
                                        "6A",
                                        "6B",
                                        "6C",
                                        "6D",
                                        "6E",
                                        "6F",
                                        "structured-experience",
                                    ],
                                    "model_responses": "synthetic mocks",
                                    "database": "SQLCipher",
                                    "errors": errors,
                                    "external": external,
                                },
                                indent=2,
                            ),
                            encoding="utf-8",
                        )
                    except BaseException:
                        (evidence / "browser-failure-diagnostics.json").write_text(
                            json.dumps(
                                {
                                    "errors": errors,
                                    "external": external,
                                    "service_exit_codes": [service.poll() for service in services],
                                },
                                indent=2,
                            ),
                            encoding="utf-8",
                        )
                        page.screenshot(
                            path=str(evidence / "phase4-browser-failure.png"),
                            full_page=True,
                        )
                        raise
                    finally:
                        browser.close()
            finally:
                for service in reversed(services):
                    stop(service)
    print(
        "PASS: Playwright A/D/E/F and Phase 6 workflows with real PDFs, "
        "encrypted storage, DOCX downloads and synthetic model responses"
    )


if __name__ == "__main__":
    main()
