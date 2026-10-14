import hashlib
import json
import math
import re
from datetime import date
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ai import repository
from app.ai.gateway import Gateway, Progress
from app.career import service as career
from app.career.schemas import CareerRecord
from app.jobs.schemas import Job, JobAnalysis, MatchAnalysis, MatchItem
from app.resumes.schemas import SourceRef
from app.settings import service as settings

ALIASES: dict[str, list[str]] = {
    "javascript": ["js", "ecmascript"],
    "typescript": ["ts"],
    "kubernetes": ["k8s"],
    "postgresql": ["postgres"],
    "continuous integration": ["ci"],
    "continuous delivery": ["cd"],
    "ci/cd": [
        "continuous integration and continuous delivery",
        "continuous integration/continuous delivery",
    ],
    "amazon web services": ["aws"],
    "node.js": ["nodejs", "node js"],
    ".net": ["dotnet"],
}


def normalized(text: str) -> str:
    return " ".join(text.casefold().split())


def canonical_term(term: str, aliases: dict[str, list[str]]) -> str:
    term = normalized(term)
    return next(
        (
            canonical
            for canonical, alternatives in aliases.items()
            if term in [canonical, *alternatives]
        ),
        term,
    )


def contains(text: str, term: str, aliases: dict[str, list[str]]) -> bool:
    term = normalized(term)
    variants = {term}
    for canonical, alternatives in aliases.items():
        if term in [canonical, *alternatives]:
            variants.update([canonical, *alternatives])
    return any(
        re.search(
            r"(?<!\w)" + re.escape(v) + (r"(?![\w+#])" if v[-1].isalnum() else r"(?!\w)"),
            normalized(text),
        )
        for v in variants
        if v
    )


def record_text(record: CareerRecord) -> str:
    data = record.data.model_dump(mode="json", exclude={"type"})
    # UUID links and dates are metadata, not relevance keywords.
    return " ".join(
        str(v) if not isinstance(v, (dict, list)) else json.dumps(v, ensure_ascii=False)
        for k, v in data.items()
        if not k.endswith("_id") and "date" not in k and v is not None
    )


def cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise HTTPException(
            502, "Embedding dimensions changed. Choose a consistent embedding model."
        )
    norm = math.sqrt(sum(v * v for v in left) * sum(v * v for v in right))
    return (
        max(0.0, min(1.0, sum(a * b for a, b in zip(left, right, strict=True)) / norm))
        if norm
        else 0.0
    )


def career_records(db: Session, owner: UUID) -> list[CareerRecord]:
    repository.refresh_session(db)
    records = []
    for kind in ("experience", "achievement", "project", "skill"):
        records.extend(career.list_records(db, owner, kind))
    return sorted(records, key=lambda r: str(r.id))


def snapshot_digest(records: list[CareerRecord]) -> str:
    return hashlib.sha256(
        json.dumps([r.model_dump(mode="json") for r in records], sort_keys=True).encode()
    ).hexdigest()


async def match(
    db: Session,
    owner: UUID,
    job: Job,
    analysis: JobAnalysis,
    gateway: Gateway,
    use_embeddings: bool,
    progress: Progress | None = None,
) -> MatchAnalysis:
    records = career_records(db, owner)
    snapshot = snapshot_digest(records)
    aliases = {k: list(v) for k, v in ALIASES.items()}
    for record in records:
        if record.data.type == "skill":
            aliases.setdefault(normalized(record.data.name), []).extend(
                normalized(a) for a in record.data.aliases
            )
    keywords: dict[str, int] = {}
    for kw in analysis.keywords:
        term = canonical_term(kw.term, aliases)
        keywords[term] = max(keywords.get(term, 0), kw.weight)
    for req in analysis.required_skills:
        keywords[canonical_term(req.term, aliases)] = max(
            5, keywords.get(canonical_term(req.term, aliases), 0)
        )
    for req in analysis.preferred_skills:
        keywords.setdefault(canonical_term(req.term, aliases), 2)
    warnings = []
    embed_config = None
    if use_embeddings:
        try:
            embed_config = settings.resolve(db, owner, "embeddings")
        except HTTPException as error:
            if error.status_code != 409:
                raise
            warnings.append("No embedding model assigned. Matching uses keywords only.")
    job_vector = None
    vectors: dict[UUID, list[float]] = {}
    if embed_config and records:
        endpoint, profile = embed_config
        model_key = hashlib.sha256(
            f"{endpoint.id}:{endpoint.base_url}:{profile.model}:{profile.context_window}:v1".encode()
        ).hexdigest()

        async def vector(kind: str, identifier: UUID, text: str) -> list[float]:
            digest = hashlib.sha256(text.encode()).hexdigest()
            cached = repository.embedding(db, owner, kind, identifier, model_key, digest)
            if cached is not None:
                return cached
            result = await gateway.embed(endpoint, profile, text)
            repository.save_embedding(db, owner, kind, identifier, model_key, digest, result)
            return result

        query = (
            "search_query: " + " ".join(keywords) if keywords else "search_query: " + job.raw_text
        )
        job_vector = await vector("job", job.id, query)
        for index, record in enumerate(records):
            if progress:
                await progress(f"Matching career evidence {index + 1}/{len(records)}")
            vectors[record.id] = await vector(
                record.data.type, record.id, "search_document: " + record_text(record)
            )
    total = sum(keywords.values())
    matched_all: set[str] = set()
    items = []
    for record in records:
        text = record_text(record)
        matched = [term for term in keywords if contains(text, term, aliases)]
        matched_all.update(matched)
        keyword_score = sum(keywords[t] for t in matched) / total if total else 0
        semantic = cosine(job_vector, vectors[record.id]) if job_vector is not None else None
        data = record.data.model_dump(mode="json")
        recency = 0.0
        for field in ("end_date", "last_used_date", "start_date"):
            if data.get(field):
                years = max(0, (date.today() - date.fromisoformat(str(data[field]))).days / 365.25)
                recency = 1 / (1 + years)
                break
        if data.get("current"):
            recency = 1
        importance = float(data.get("importance", 3)) / 5
        base = 0.6 * keyword_score + 0.3 * semantic if semantic is not None else 0.9 * keyword_score
        score = (
            base + 0.05 * recency + 0.05 * importance if (matched or semantic is not None) else 0.0
        )
        label = next(
            (str(data[k]) for k in ("text", "name", "job_title") if data.get(k)), record.data.type
        )
        reasons = ["Career source matches: " + ", ".join(matched)] if matched else []
        if semantic is not None:
            reasons.append("Semantic similarity is a relevance signal, not proof of a skill")
        items.append(
            MatchItem(
                source_ref=SourceRef(entity_type=record.data.type, entity_id=record.id),
                label=label,
                score=round(score * 100, 2),
                keyword_score=round(keyword_score * 100, 2),
                semantic_score=round(semantic * 100, 2) if semantic is not None else None,
                matched_keywords=matched,
                reasons=reasons,
            )
        )
    items.sort(key=lambda item: (-item.score, str(item.source_ref.entity_id)))
    if snapshot_digest(career_records(db, owner)) != snapshot:
        raise HTTPException(409, "Career library changed during matching. Retry the saved job.")
    return MatchAnalysis(
        items=items,
        missing_keywords=[t for t in keywords if t not in matched_all],
        strengths=sorted(matched_all),
        emphasis_areas=[i.label for i in items[:5] if i.score > 0],
        keyword_coverage=round(sum(keywords[t] for t in matched_all) / total * 100, 2)
        if total
        else 0,
        retrieval_mode="embeddings_and_keywords" if job_vector is not None else "keywords",
        warnings=warnings,
        career_snapshot_hash=snapshot,
    )
