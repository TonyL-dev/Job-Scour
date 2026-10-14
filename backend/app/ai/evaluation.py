import argparse
import asyncio
import json
import re
import time
from importlib.resources import files
from pathlib import Path
from typing import Literal, TypedDict
from uuid import uuid4

from fastapi import HTTPException

from app.ai.gateway import Gateway
from app.ai.prompts import job_prompt, validate_evidence
from app.ai.retrieval import ALIASES, canonical_term, contains
from app.ai.service import EXTRACTION_VERSION, analyze_job
from app.jobs.schemas import JobAnalysis
from app.settings.schemas import Endpoint, Profile


class EvaluationCase(TypedDict):
    key: str
    text: str
    required: list[str]
    preferred: list[str]
    forbidden: list[str]
    career_profile: str
    matched: list[str]
    gaps: list[str]
    seniority: str | None
    years: str | None
    page_limit: int


def fixtures() -> list[EvaluationCase]:
    result: list[EvaluationCase] = json.loads(
        files("app.ai").joinpath("evaluation/jobs.json").read_text(encoding="utf-8")
    )
    return result


def assess(analysis: JobAnalysis, case: EvaluationCase) -> list[str]:
    errors = []
    try:
        validate_evidence(analysis, str(case["text"]))
    except ValueError:
        errors.append("unsupported_evidence")
    required = " | ".join(r.term for r in analysis.required_skills)
    preferred = " | ".join(r.term for r in analysis.preferred_skills)
    for term in case["required"]:
        if not contains(required, str(term), ALIASES):
            errors.append(f"missing_required:{term}")
    for term in case["preferred"]:
        if not contains(preferred, str(term), ALIASES):
            errors.append(f"missing_preferred:{term}")
        if contains(required, str(term), ALIASES):
            errors.append(f"preferred_became_required:{term}")
    terms = " | ".join(
        r.term
        for r in [
            *analysis.required_skills,
            *analysis.preferred_skills,
            *analysis.technologies,
            *analysis.responsibilities,
            *analysis.company_values,
            *analysis.industry_terms,
            *analysis.keywords,
        ]
    )
    for term in case["forbidden"]:
        if contains(terms, str(term), ALIASES):
            errors.append(f"fabricated_or_injected:{term}")
    for field, expected in (
        (analysis.seniority, case["seniority"]),
        (analysis.years_experience, case["years"]),
    ):
        if expected is None and field is not None:
            errors.append("inferred_unstated_seniority_or_years")
        elif expected is not None and (
            field is None
            or not (
                re.search(r"(?<!\d)" + re.escape(expected) + r"(?!\d)", field.term)
                if expected.isdigit()
                else contains(field.term, expected, ALIASES)
            )
        ):
            errors.append("missing_stated_seniority_or_years")
    requirement_terms = [r.term for r in [*analysis.required_skills, *analysis.preferred_skills]]
    evidenced = " | ".join(
        term for term in requirement_terms if contains(case["career_profile"], term, ALIASES)
    )
    for term in case["matched"]:
        if not contains(evidenced, term, ALIASES):
            errors.append(f"missing_career_match:{term}")
    for term in case["gaps"]:
        if contains(evidenced, term, ALIASES):
            errors.append(f"gap_became_career_fact:{term}")
    return errors


async def evaluate(
    models: list[str],
    base_url: str,
    repeats: int,
    context: int,
    mode: Literal["json_schema", "json_object", "none"] = "json_schema",
    max_output: int = 4096,
    cases: list[str] | None = None,
    provider: Literal["codex", "openai_compatible"] = "openai_compatible",
) -> dict[str, object]:
    gateway = Gateway()
    endpoint = Endpoint(
        id=uuid4(),
        name="Synthetic evaluation only",
        provider=provider,
        base_url="https://chatgpt.com/codex" if provider == "codex" else base_url,
        remote_consent=provider == "codex",
    )
    prompt = job_prompt()
    results = []
    for model in models:
        profile = Profile(
            id=uuid4(),
            endpoint_id=endpoint.id,
            model=model,
            context_window=context,
            max_output_tokens=max_output,
            temperature=0,
            structured_mode=mode,
        )
        for case in fixtures():
            if cases and case["key"] not in cases:
                continue
            previous: set[str] | None = None
            for repetition in range(repeats):
                start = time.monotonic()
                errors = []
                analysis = None
                try:
                    analysis = await analyze_job(gateway, endpoint, profile, case["text"], prompt)
                    errors = assess(analysis, case)
                    projection = {canonical_term(r.term, ALIASES) for r in analysis.required_skills}
                    if previous is not None and projection != previous:
                        errors.append("unstable_required_skills")
                    previous = projection
                except Exception as error:
                    # No endpoint response bodies, secrets, or personal data in reports.
                    errors = [f"request_failed:{type(error).__name__}"]
                    if isinstance(error, HTTPException):
                        errors.append(f"HTTP_{error.status_code}:{error.detail}")
                result = {
                    "model": model,
                    "case": case["key"],
                    "repeat": repetition + 1,
                    "passed": not errors,
                    "errors": errors,
                    "seconds": round(time.monotonic() - start, 2),
                    "analysis": analysis.model_dump(mode="json") if analysis else None,
                }
                results.append(result)
                print(
                    f"{model} / {case['key']} / {repetition + 1}: "
                    f"{'PASS' if not errors else errors}",
                    flush=True,
                )
    return {
        "prompt_digest": prompt.digest,
        "prompt_version": f"{prompt.key}:v{prompt.version}",
        "extraction_version": EXTRACTION_VERSION,
        "structured_mode": mode,
        "context_window": context,
        "max_output_tokens": max_output,
        "fixture_count": sum(1 for case in fixtures() if not cases or case["key"] in cases),
        "deferred_checks": ["resume_rewrite_provenance", "locks", "two_page_fitting"],
        "passed": all(r["passed"] for r in results),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run synthetic job-analysis evaluation through Codex or a local endpoint. "
        "No career database is read."
    )
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--provider", choices=["codex", "openai_compatible"], default="codex")
    parser.add_argument("--base-url", default="http://127.0.0.1:1234/v1")
    parser.add_argument("--repeats", type=int, default=2, choices=range(1, 6))
    parser.add_argument("--context", type=int, default=131072)
    parser.add_argument(
        "--structured-mode", choices=["json_schema", "json_object", "none"], default="json_schema"
    )
    parser.add_argument("--max-output", type=int, default=4096)
    parser.add_argument("--cases", nargs="+", choices=[c["key"] for c in fixtures()])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = asyncio.run(
        evaluate(
            args.models,
            args.base_url,
            args.repeats,
            args.context,
            args.structured_mode,
            args.max_output,
            args.cases,
            args.provider,
        )
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
