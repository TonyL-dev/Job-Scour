"""Live synthetic Phase 3 evaluation in disposable databases; never opens the career database."""

import argparse
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.ai.evaluation import fixtures
from app.ai.retrieval import ALIASES, contains
from app.core.config import Settings, get_settings
from app.main import create_app


def evaluate(args: argparse.Namespace) -> dict[str, object]:
    results: list[dict[str, object]] = []
    for model in args.models:
        for case in fixtures():
            if args.cases and case["key"] not in args.cases:
                continue
            started = time.monotonic()
            errors: list[str] = []
            run = None
            with tempfile.TemporaryDirectory(prefix="resume-generation-eval-") as temporary:
                url = f"sqlite:///{Path(temporary) / 'synthetic.db'}"
                previous = os.environ.get("APP_DATABASE_URL")
                os.environ["APP_DATABASE_URL"] = url
                get_settings.cache_clear()
                try:
                    command.upgrade(Config("alembic.ini"), "head")
                    with TestClient(
                        create_app(Settings(database_url=url, mode="local", _env_file=None))
                    ) as client:
                        endpoint = client.post(
                            "/api/settings/endpoints",
                            json={
                                "name": "Synthetic evaluation",
                                "provider": args.provider,
                                "base_url": "https://chatgpt.com/codex"
                                if args.provider == "codex"
                                else args.base_url,
                                "remote_consent": args.provider == "codex",
                            },
                        )
                        if endpoint.status_code != 201:
                            raise RuntimeError("Evaluation endpoint configuration failed")
                        profile = client.post(
                            "/api/settings/profiles",
                            json={
                                "endpoint_id": endpoint.json()["id"],
                                "model": model,
                                "context_window": args.context,
                                "max_output_tokens": args.max_output,
                                "temperature": 0,
                                "structured_mode": args.structured_mode,
                            },
                        ).json()
                        for task in (
                            "job_analysis",
                            "ranking",
                            "rewriting",
                            "summary",
                            "verification",
                            "condensing",
                        ):
                            response = client.put(
                                "/api/settings/assignments",
                                json={"task": task, "profile_id": profile["id"]},
                            )
                            response.raise_for_status()
                        experience = client.post(
                            "/api/career",
                            json={
                                "type": "experience",
                                "company": "Synthetic employer",
                                "job_title": "Stored title",
                                "start_date": "2020-01-01",
                                "current": True,
                            },
                        ).json()
                        achievement = client.post(
                            "/api/career",
                            json={
                                "type": "achievement",
                                "experience_id": experience["id"],
                                "text": case["career_profile"],
                                "importance": 5,
                            },
                        ).json()
                        for term in case["matched"]:
                            client.post(
                                "/api/career", json={"type": "skill", "name": term}
                            ).raise_for_status()
                        ref = {"entity_type": "achievement", "entity_id": achievement["id"]}
                        content: dict[str, Any] = {
                            "schema_version": 1,
                            "header": {"name": "Synthetic evaluation candidate"},
                            "sections": [
                                {
                                    "key": str(uuid4()),
                                    "type": "summary",
                                    "title": "Summary",
                                    "items": [],
                                },
                                {
                                    "key": str(uuid4()),
                                    "type": "experience",
                                    "title": "Experience",
                                    "items": [
                                        {
                                            "key": str(uuid4()),
                                            "text": case["career_profile"],
                                            "origin": "user",
                                            "source_refs": [ref],
                                            "locked": protected,
                                        }
                                        for protected in (True, False)
                                    ],
                                },
                                {
                                    "key": str(uuid4()),
                                    "type": "skills",
                                    "title": "Skills",
                                    "items": [],
                                },
                            ],
                            "metadata": {
                                "template_id": "00000000-0000-4000-8000-000000000101",
                                "target_page_limit": 2,
                            },
                        }
                        master = client.post(
                            "/api/resumes", json={"title": "Synthetic master", "content": content}
                        ).json()
                        job = client.post("/api/jobs", json={"raw_text": case["text"]}).json()
                        response = client.post(
                            "/api/generation",
                            json={
                                "master_id": master["id"],
                                "job_id": job["id"],
                                "use_embeddings": False,
                            },
                        )
                        response.raise_for_status()
                        identifier = response.json()["id"]
                        last_stage = ""
                        while True:
                            run = client.get(f"/api/generation/{identifier}").json()
                            stage = run["events"][-1]["stage"] if run["events"] else "Queued"
                            if stage != last_stage:
                                print(f"{model} / {case['key']}: {stage}", flush=True)
                                last_stage = stage
                            if run["status"] not in {"queued", "running"}:
                                break
                            if time.monotonic() - started > 900:
                                client.post(f"/api/generation/{identifier}/cancel")
                                raise TimeoutError("Evaluation run exceeded fifteen minutes")
                            time.sleep(0.2)
                        if run["status"] != "succeeded":
                            errors.append(f"run_{run['status']}:{run['error']}")
                        else:
                            proposed = run["proposed"]
                            if run["page_count"] > 2:
                                errors.append("page_limit")
                            if (
                                proposed["metadata"]["template_id"]
                                != content["metadata"]["template_id"]
                            ):
                                errors.append("template_changed")
                            if (
                                proposed["sections"][1]["items"][0]
                                != master["content"]["sections"][1]["items"][0]
                            ):
                                errors.append("lock_changed")
                            generated = [
                                i
                                for s in proposed["sections"]
                                for i in s["items"]
                                if i["origin"] == "ai"
                            ]
                            if not any(
                                s["verification"] == "supported"
                                and s["proposed"]
                                and s["proposed"]["origin"] == "ai"
                                and s["section_key"] != proposed["sections"][2]["key"]
                                for s in run["suggestions"]
                            ):
                                errors.append("no_supported_rewrite")
                            for item in generated:
                                if not item["source_refs"]:
                                    errors.append("missing_provenance")
                                for term in [*case["forbidden"], *case["gaps"]]:
                                    if contains(item["text"], term, ALIASES):
                                        errors.append(f"unsupported_claim:{term}")
                            decisions = [
                                {
                                    "suggestion_id": s["id"],
                                    "action": "accept"
                                    if s["verification"] == "supported"
                                    else "reject",
                                }
                                for s in run["suggestions"]
                            ]
                            saved = client.post(
                                f"/api/generation/{identifier}/commit",
                                json={"title": "Reviewed evaluation", "decisions": decisions},
                            )
                            if saved.status_code != 201:
                                errors.append("review_commit_failed")
                except Exception as error:
                    errors.append(f"evaluation_failed:{type(error).__name__}")
                finally:
                    if previous is None:
                        os.environ.pop("APP_DATABASE_URL", None)
                    else:
                        os.environ["APP_DATABASE_URL"] = previous
                    get_settings.cache_clear()
            results.append(
                {
                    "model": model,
                    "case": case["key"],
                    "passed": not errors,
                    "errors": errors,
                    "seconds": round(time.monotonic() - started, 2),
                    "run": run,
                }
            )
            print(f"{model} / {case['key']}: {'PASS' if not errors else errors}", flush=True)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(
                    json.dumps(
                        {"passed": all(r["passed"] for r in results), "results": results}, indent=2
                    ),
                    encoding="utf-8",
                )
    return {"passed": bool(results) and all(r["passed"] for r in results), "results": results}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--provider", choices=["codex", "openai_compatible"], default="codex")
    parser.add_argument("--base-url", default="http://127.0.0.1:1234/v1")
    parser.add_argument("--context", type=int, default=131072)
    parser.add_argument("--max-output", type=int, default=2048)
    parser.add_argument(
        "--structured-mode", choices=["json_schema", "json_object", "none"], default="json_schema"
    )
    parser.add_argument("--cases", nargs="+", choices=[c["key"] for c in fixtures()])
    parser.add_argument("--output", type=Path)
    report = evaluate(parser.parse_args())
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
