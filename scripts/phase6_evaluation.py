"""Fresh model evaluations in disposable synthetic stores; never opens career databases."""

import argparse
import json
import os
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=["default"])
    parser.add_argument(
        "--tasks", nargs="+", default=["import_extraction", "profile_questions", "cover_letter"]
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.output.is_absolute():
        args.output = Path(__file__).resolve().parents[1] / args.output
    report: dict[str, object] = {
        "provider": "codex",
        "model_calls": "fresh, synthetic only",
        "results": [],
    }
    results: list[dict[str, object]] = []
    original = {
        key: os.environ.get(key)
        for key in (
            "APP_DATABASE_URL",
            "APP_DATABASE_PASSPHRASE",
            "APP_ENCRYPTION_KEY",
            "APP_UPLOAD_KEY",
        )
    }
    try:
        for model in args.models:
            with tempfile.TemporaryDirectory(prefix="stonks-phase6-model-") as folder:
                for key in original:
                    os.environ.pop(key, None)
                url = f"sqlite:///{Path(folder) / 'synthetic.db'}"
                os.environ["APP_DATABASE_URL"] = url
                get_settings.cache_clear()
                config = Config("alembic.ini")
                command.upgrade(config, "head")
                with TestClient(create_app(Settings(database_url=url))) as client:
                    endpoint = client.post(
                        "/api/settings/endpoints",
                        json={
                            "name": "Synthetic Codex evaluation",
                            "provider": "codex",
                            "base_url": "https://chatgpt.com/codex",
                            "remote_consent": True,
                        },
                    ).json()
                    profile = client.post(
                        "/api/settings/profiles",
                        json={
                            "endpoint_id": endpoint["id"],
                            "model": model,
                            "context_window": 131072,
                            "max_output_tokens": 4096,
                        },
                    ).json()
                    for task in set(args.tasks) | {"verification"}:
                        response = client.put(
                            "/api/settings/assignments",
                            json={"task": task, "profile_id": profile["id"]},
                        )
                        response.raise_for_status()
                    for task in args.tasks:
                        prompt = client.post(
                            "/api/prompts",
                            json={
                                "task": task,
                                "name": f"Synthetic {task} acceptance",
                                "tone": "plain",
                                "focus": "clarity",
                            },
                        ).json()
                        response = client.post(f"/api/prompts/{prompt['id']}/evaluate")
                        entry = {
                            "model": model,
                            "task": task,
                            "status_code": response.status_code,
                            "report": response.json(),
                        }
                        results.append(entry)
                        report["results"] = results
                        report["passed"] = all(
                            isinstance(r["report"], dict) and r["report"].get("passed") is True
                            for r in results
                        )
                        args.output.parent.mkdir(parents=True, exist_ok=True)
                        args.output.write_text(
                            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
                        )
                        status = "PASS" if entry["report"].get("passed") else "FAIL"
                        print(
                            f"{model}: {task}: {status}",
                            flush=True,
                        )
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        get_settings.cache_clear()
    if not report.get("passed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
