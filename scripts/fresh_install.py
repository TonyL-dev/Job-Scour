"""README installation in a disposable source copy with new dependency environments."""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


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
    raise RuntimeError("Installation service did not become ready")


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


def smoke(evidence: Path) -> None:
    from playwright.sync_api import expect, sync_playwright

    backend = ROOT / "backend"
    pnpm = shutil.which("pnpm") or shutil.which("pnpm.cmd")
    assert pnpm
    api_port, web_port = port(), port()
    url = f"http://127.0.0.1:{web_port}"
    env = dict(os.environ)
    env.update(
        APP_API_PORT=str(api_port),
        APP_FRONTEND_ORIGINS=json.dumps([url]),
        API_PROXY_TARGET=f"http://127.0.0.1:{api_port}",
    )
    options = (
        {"creationflags": subprocess.CREATE_NO_WINDOW}
        if os.name == "nt"
        else {"start_new_session": True}
    )
    services: list[subprocess.Popen] = []
    with (evidence / "fresh-install-runtime.log").open("w", encoding="utf-8") as log:
        try:

            def start_backend() -> subprocess.Popen:
                process = subprocess.Popen(
                    [sys.executable, "-m", "app"],
                    cwd=backend,
                    env=env,
                    stdout=log,
                    stderr=log,
                    **options,
                )
                services.append(process)
                return process

            process = start_backend()
            services.append(
                subprocess.Popen(
                    [
                        pnpm,
                        "exec",
                        "vite",
                        "preview",
                        "--port",
                        str(web_port),
                        "--strictPort",
                    ],
                    cwd=ROOT / "frontend",
                    env=env,
                    stdout=log,
                    stderr=log,
                    **options,
                )
            )
            wait(url + "/api/health")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    page = browser.new_page()
                    errors: list[str] = []
                    external: list[str] = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on(
                        "request",
                        lambda request: (
                            external.append(request.url)
                            if not request.url.startswith((url, "blob:", "data:"))
                            else None
                        ),
                    )
                    page.goto(url)
                    expect(page.get_by_text("Backend connected")).to_be_visible(timeout=15000)
                    page.keyboard.press("Tab")
                    expect(page.get_by_role("link", name="Skip to main content")).to_be_focused()
                    page.keyboard.press("Enter")
                    expect(page.locator("#main-content")).to_be_focused()
                    page.get_by_role("link", name="Master resumes", exact=True).click()
                    expect(page.locator("#main-content")).to_be_focused()
                    page.get_by_label("Resume title", exact=True).fill("Installation master")
                    page.get_by_label("Full name *", exact=True).fill("Fresh Install Example")
                    page.get_by_role("button", name="Add section", exact=True).click()
                    page.get_by_role("button", name="Add manual text", exact=True).click()
                    page.get_by_label("Item text", exact=True).fill(
                        "Synthetic installation smoke test."
                    )
                    expect(page.locator(".pdf-pages canvas").first).to_be_visible(timeout=60000)
                    with page.expect_download() as download:
                        page.get_by_role("button", name="Save & download PDF", exact=True).click()
                    download.value.save_as(str(evidence / "fresh-install.pdf"))
                    page.get_by_role("link", name="Resume history & ATS", exact=True).click()
                    page.get_by_label("Resume history document", exact=True).select_option(
                        label="Installation master · master"
                    )
                    page.get_by_role(
                        "button", name="Run ATS checks on this PDF", exact=True
                    ).click()
                    # Wait for a persisted report rather than depending on its heuristic score.
                    expect(page.get_by_role("heading", name="/100", exact=False)).to_be_visible(
                        timeout=60000
                    )
                    stop(process)
                    page.reload()
                    expect(
                        page.get_by_role("heading", name="Workspace unavailable")
                    ).to_be_visible()
                    start_backend()
                    wait(url + "/api/health")
                    page.get_by_role("button", name="Retry connection", exact=True).click()
                    expect(page.get_by_label("Resume history document")).to_contain_text(
                        "Installation master"
                    )
                    assert not errors and not external, (errors, external)
                    page.screenshot(
                        path=str(evidence / "fresh-install-desktop.png"), full_page=True
                    )
                    page.set_viewport_size({"width": 390, "height": 844})
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    page.screenshot(path=str(evidence / "fresh-install-mobile.png"), full_page=True)
                    (evidence / "fresh-install.json").write_text(
                        json.dumps(
                            {
                                "passed": True,
                                "python": sys.version.split()[0],
                                "environment": "new dependency environments; existing host OS",
                                "workflow": "production UI, keyboard, PDF, ATS, outage/restart",
                                "model_calls": 0,
                                "errors": errors,
                                "external": external,
                            },
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                finally:
                    browser.close()
        finally:
            for service in reversed(services):
                stop(service)


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--smoke":
        smoke(Path(sys.argv[2]))
        return
    evidence = ROOT / ".validation"
    evidence.mkdir(exist_ok=True)
    # Explicit source allowlist: never copy local databases, environment files or credentials.
    with tempfile.TemporaryDirectory(prefix="phase5-install-", dir=evidence) as directory:
        target = Path(directory)
        for domain, folders, files in (
            (
                "backend",
                ["app", "migrations"],
                ["pyproject.toml", "requirements.lock", "alembic.ini"],
            ),
            (
                "frontend",
                ["src"],
                [
                    "package.json",
                    "pnpm-lock.yaml",
                    "tsconfig.json",
                    "vite.config.ts",
                    "index.html",
                    "eslint.config.js",
                ],
            ),
            ("scripts", [], ["tasks.py", "fresh_install.py", "phase6_evaluation.py"]),
        ):
            (target / domain).mkdir()
            for folder in folders:
                shutil.copytree(
                    ROOT / domain / folder,
                    target / domain / folder,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                )
            for file in files:
                shutil.copy2(ROOT / domain / file, target / domain / file)
        env = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith(("APP_", "LLM_", "STONKS_", "API_PROXY_"))
        }
        env["PYTHONUTF8"] = "1"
        for variable in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "PIP_CERT"):
            env.pop(variable, None)
        python = (
            target / "backend/.venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        )
        with (evidence / "fresh-install-setup.log").open("w", encoding="utf-8") as log:
            for task in ("setup", "renderer-setup", "migrate", "doctor"):
                print("Fresh source: " + task, flush=True)
                subprocess.run(
                    [sys.executable, "scripts/tasks.py", task],
                    cwd=target,
                    env=env,
                    check=True,
                    stdout=log,
                    stderr=log,
                )
            pnpm = shutil.which("pnpm") or shutil.which("pnpm.cmd")
            assert pnpm
            subprocess.run(
                [pnpm, "build"],
                cwd=target / "frontend",
                env=env,
                check=True,
                stdout=log,
                stderr=log,
            )
            subprocess.run(
                [str(python), "scripts/fresh_install.py", "--smoke", str(evidence)],
                cwd=target,
                env=env,
                check=True,
                stdout=log,
                stderr=log,
            )
    print("PASS: isolated README install and production browser workflow; evidence in .validation")


if __name__ == "__main__":
    main()
