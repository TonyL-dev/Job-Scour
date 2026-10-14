"""Synthetic model responses for isolated browser tests, never product imports."""

import json
from uuid import UUID, uuid4

import httpx
from test_phase2 import ANALYSIS, sse
from test_phase3 import transport

from app.ai.generation import claim_check
from app.ai.prompt_evaluation import SOURCE


def phase6_transport() -> httpx.MockTransport:
    fallback = transport()

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        kind = payload["response_format"]["json_schema"]["name"]
        user = payload["messages"][1]["content"]
        context = json.loads(user.split("DATA:\n", 1)[1]) if "DATA:\n" in user else {}
        if kind == "Questions":
            return sse(
                {"questions": ["What outcome did you observe?", "How did you measure the change?"]}
            )
        if kind == "Extraction":
            fragment = context[0]
            name = "Synthetic Orbit" if "Synthetic Orbit" in fragment["text"] else "Orbit"
            return sse(
                {
                    "candidates": [
                        {
                            "key": "project",
                            "data": {
                                "type": "project",
                                "name": name,
                                "description": fragment["text"],
                            },
                            "locator": fragment["locator"],
                            "excerpt": fragment["text"],
                        }
                    ]
                }
            )
        if kind == "Paragraphs":
            identifier, raw = next(iter(context["sources"].items()))
            facts = json.loads(raw)
            text = facts.get("text", facts.get("description", "")).split(
                "\nUNTRUSTED INSTRUCTION:"
            )[0]
            return sse(
                {
                    "paragraphs": [
                        {
                            "key": str(uuid4()),
                            "text": text,
                            "origin": "ai",
                            "source_refs": [
                                {"entity_type": facts["record_type"], "entity_id": identifier}
                            ],
                        }
                    ]
                }
            )
        if kind == "Rewrite" and str(SOURCE) in context.get("sources", {}):
            facts = json.loads(context["sources"][str(SOURCE)])
            return sse(
                {
                    "text": facts["description"].split("\nUNTRUSTED INSTRUCTION:")[0],
                    "source_ids": [str(SOURCE)],
                }
            )
        if kind == "Verification":
            sources = context["sources"]
            rejected = claim_check(
                context["text"],
                {UUID(k): v for k, v in sources.items()},
                [UUID(k) for k in sources],
                [],
            )
            return sse(
                {
                    "status": "unsupported" if rejected else "supported",
                    "reason": rejected or "Synthetic source comparison",
                }
            )
        if kind == "JobAnalysis" and "Untrusted text:" in user:
            result = json.loads(json.dumps(ANALYSIS))
            result["required_skills"] = [
                r for r in result["required_skills"] if r["term"] != "Kubernetes"
            ]
            return sse(result)
        return fallback.handle_request(request)

    return httpx.MockTransport(handler)
