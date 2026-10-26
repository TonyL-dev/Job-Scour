"""Cross-platform task runner. Run python scripts/tasks.py --help."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
PYTHON = BACKEND / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run(*args: str, cwd: Path = ROOT) -> None:
    print(f"> {' '.join(args)}", flush=True)
    subprocess.run(args, cwd=cwd, check=True)


def pnpm(*args: str) -> None:
    executable = shutil.which("pnpm") or shutil.which("pnpm.cmd")
    if not executable:
        raise SystemExit("Install pnpm 11.19.0 or add it to PATH.")
    run(executable, *args, cwd=FRONTEND)


def runtimes() -> None:
    if sys.version_info < (3, 12):  # noqa: UP036 -- runner also runs before creating the venv
        raise SystemExit("Python 3.12 or newer is required.")
    for tool, expected in (("node", "24"), ("pnpm", "11.19.0")):
        executable = shutil.which(tool) or shutil.which(tool + ".cmd")
        if not executable:
            raise SystemExit(f"Install {tool} {expected} and add it to PATH.")
        version = subprocess.check_output([executable, "--version"], text=True).strip().lstrip("v")
        if (tool == "node" and version.split(".")[0] != expected) or (
            tool == "pnpm" and version != expected
        ):
            raise SystemExit(f"Expected {tool} {expected}; found {version}.")


def api(check: bool = False) -> None:
    run(str(PYTHON), "scripts/export_openapi.py", *(["--check"] if check else []))
    if not check:
        pnpm("api:generate")
        return
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory) / "schema.d.ts"
        pnpm("exec", "openapi-typescript", "src/api/openapi.json", "-o", str(temporary))
        if temporary.read_bytes() != (FRONTEND / "src/api/schema.d.ts").read_bytes():
            raise SystemExit("API types are stale. Run python scripts/tasks.py api.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "task",
        choices=[
            "setup",
            "hooks",
            "api",
            "api-check",
            "check",
            "migrate",
            "backend",
            "frontend",
            "up",
            "down",
            "audit",
            "renderer-setup",
            "ai-eval",
            "generation-eval",
            "phase6-eval",
            "e2e",
            "doctor",
            "fresh-install",
        ],
    )
    args, extra = parser.parse_known_args()
    task = args.task
    if extra and task not in {"ai-eval", "generation-eval", "phase6-eval"}:
        parser.error("Extra arguments are supported only for evaluation tasks")
    if task == "setup":
        runtimes()
        if not PYTHON.exists():
            run(sys.executable, "-m", "venv", str(BACKEND / ".venv"))
        run(str(PYTHON), "-m", "pip", "install", "-r", "requirements.lock", cwd=BACKEND)
        run(
            str(PYTHON),
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--no-build-isolation",
            "-e",
            ".",
            cwd=BACKEND,
        )
        pnpm("install", "--frozen-lockfile")
    elif task == "doctor":
        runtimes()
        run(str(PYTHON), "-m", "app.health.doctor", cwd=BACKEND)
    elif task == "fresh-install":
        runtimes()
        run(sys.executable, "scripts/fresh_install.py")
    elif task == "e2e":
        run(str(PYTHON), "scripts/e2e.py")
        run(str(PYTHON), "scripts/ui_style.py", "browser")
    elif task == "hooks":
        run(str(PYTHON), "-m", "pre_commit", "install")
    elif task == "renderer-setup":
        run(str(PYTHON), "-m", "playwright", "install", "chromium")
    elif task == "ai-eval":
        run(str(PYTHON), "-m", "app.ai.evaluation", *extra, cwd=BACKEND)
    elif task == "generation-eval":
        run(str(PYTHON), "-m", "app.ai.generation_evaluation", *extra, cwd=BACKEND)
    elif task == "phase6-eval":
        run(str(PYTHON), "../scripts/phase6_evaluation.py", *extra, cwd=BACKEND)
    elif task in {"api", "api-check"}:
        api(check=task == "api-check")
    elif task == "check":
        run(sys.executable, "scripts/ui_style.py", "check")
        run(
            str(PYTHON),
            "-m",
            "ruff",
            "check",
            "app",
            "tests",
            "migrations",
            "../scripts",
            cwd=BACKEND,
        )
        run(
            str(PYTHON),
            "-m",
            "ruff",
            "format",
            "--check",
            "app",
            "tests",
            "migrations",
            "../scripts",
            cwd=BACKEND,
        )
        run(str(PYTHON), "-m", "mypy", cwd=BACKEND)
        run(str(PYTHON), "-m", "pytest", "-q", cwd=BACKEND)
        api(check=True)
        for command in ["lint", "typecheck", "test", "build"]:
            pnpm(command)
    elif task == "migrate":
        run(str(PYTHON), "-m", "alembic", "upgrade", "head", cwd=BACKEND)
    elif task == "backend":
        run(str(PYTHON), "-m", "app", cwd=BACKEND)
    elif task == "frontend":
        pnpm("dev")
    elif task == "up":
        run("docker", "compose", "up", "--build", "-d", "--wait")
    elif task == "down":
        run("docker", "compose", "down")
    elif task == "audit":
        run(str(PYTHON), "-m", "pip_audit", "-r", "requirements.lock", cwd=BACKEND)
        pnpm("audit")


if __name__ == "__main__":
    main()
