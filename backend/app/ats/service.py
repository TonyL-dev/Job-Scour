import re
from html.parser import HTMLParser
from io import BytesIO
from uuid import UUID, uuid4

from fastapi import HTTPException
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.ai.retrieval import (
    ALIASES,
    canonical_term,
    career_records,
    contains,
    normalized,
    record_text,
)
from app.ats import repository as repo
from app.ats.schemas import Finding, Report, ReportInput
from app.core.database import utc_now
from app.resumes import service as resumes
from app.resumes.schemas import SourceRef

ENGINE_VERSION = "ats.1"
VERBS = set(
    (
        "achieved built created delivered designed developed improved led managed implemented "
        "reduced increased launched optimized automated analyzed collaborated maintained supported "
        "resolved tested deployed migrated saved trained established streamlined coordinated"
    ).split()
)


class VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_main = False
        self.segments: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "main":
            self.in_main = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "main":
            self.in_main = False

    def handle_data(self, data: str) -> None:
        if self.in_main and data.strip():
            self.segments.append(" ".join(data.split()))


def create(db: Session, owner: UUID, data: ReportInput) -> Report:
    version = resumes.get_version(db, owner, data.version_id)
    document = version.content
    analysis = repo.analysis(db, owner, data.analysis_id) if data.analysis_id else None
    if data.analysis_id and analysis is None:
        raise HTTPException(404, "Job analysis not found")
    records = career_records(db, owner)
    aliases = {k: list(v) for k, v in ALIASES.items()}
    for r in records:
        if r.data.type == "skill":
            aliases.setdefault(normalized(r.data.name), []).extend(
                normalized(a) for a in r.data.aliases
            )
    visible = [s for s in document.sections if s.visible]
    text = " ".join(
        [
            document.header.name,
            *[s.title + " " + " ".join(i.text for i in s.items) for s in visible],
        ]
    )
    keywords: dict[str, int] = {}
    if analysis:
        for kw in analysis.keywords:
            term = canonical_term(kw.term, aliases)
            keywords[term] = max(keywords.get(term, 0), kw.weight)
        for req in analysis.required_skills:
            keywords[canonical_term(req.term, aliases)] = 5
        for req in analysis.preferred_skills:
            term = canonical_term(req.term, aliases)
            keywords.setdefault(term, 2)
    matched = [k for k in keywords if contains(text, k, aliases)]
    missing = [k for k in keywords if k not in matched]
    findings: list[Finding] = []
    for term in missing:
        supported = [r for r in records if contains(record_text(r), term, aliases)]
        findings.append(
            Finding(
                code="available_keyword" if supported else "skill_gap",
                severity="info",
                message=f"{term}: present in your career library; consider a sourced addition."
                if supported
                else f"{term}: career evidence not found. Treat as a skill gap; do not insert it.",
                source_refs=[SourceRef(entity_type=r.data.type, entity_id=r.id) for r in supported],
            )
        )
    scores: dict[str, float] = {}
    if keywords:
        scores["keywords"] = round(
            100 * sum(keywords[k] for k in matched) / sum(keywords.values()), 1
        )
    else:
        findings.append(
            Finding(
                code="no_keywords",
                severity="info",
                message="Select a saved job analysis to assess keyword coverage.",
            )
        )
    bullets = [
        (s, i)
        for s in visible
        if s.type in {"experience", "projects", "volunteer"}
        for i in s.items
    ]
    strong = quantified = 0
    verbs: dict[str, int] = {}
    for s, i in bullets:
        words = i.text.split()
        opener = re.sub(r"[^a-z]", "", words[0].lower()) if words else ""
        strong += opener in VERBS
        verbs[opener] = verbs.get(opener, 0) + 1
        has_number = bool(re.search(r"\d", i.text))
        quantified += has_number
        if opener not in VERBS:
            findings.append(
                Finding(
                    code="action_verb",
                    severity="info",
                    message="Consider a precise action verb supported by your source.",
                    section_key=s.key,
                    item_key=i.key,
                )
            )
        if len(words) > 45:
            findings.append(
                Finding(
                    code="long_bullet",
                    severity="warning",
                    message="This bullet exceeds 45 words; consider a shorter sourced edit.",
                    section_key=s.key,
                    item_key=i.key,
                )
            )
        if not has_number:
            refs = [
                r
                for r in records
                if any(ref.entity_id == r.id for ref in i.source_refs)
                and r.data.type == "achievement"
                and r.data.metric_value is not None
            ]
            if refs:
                findings.append(
                    Finding(
                        code="available_metric",
                        severity="info",
                        message="A cited achievement has an available metric.",
                        section_key=s.key,
                        item_key=i.key,
                        source_refs=i.source_refs,
                    )
                )
        for term in matched:
            variants = [term, *aliases.get(term, [])]
            count = sum(
                len(re.findall(r"(?<!\w)" + re.escape(v) + r"(?!\w)", normalized(i.text)))
                for v in set(variants)
            )
            if count > 2:
                findings.append(
                    Finding(
                        code="stuffing",
                        severity="warning",
                        message=f"{term} repeats more than twice in one bullet.",
                        section_key=s.key,
                        item_key=i.key,
                    )
                )
    for section in visible:
        section_text = " ".join(i.text for i in section.items)
        word_count = max(1, len(section_text.split()))
        for term in matched:
            canonical = canonical_term(term, aliases)
            section_variants = {canonical, *aliases.get(canonical, [])}
            occurrences = sum(
                len(re.findall(r"(?<!\w)" + re.escape(v) + r"(?!\w)", normalized(section_text)))
                for v in section_variants
            )
            if occurrences > 5 and occurrences / word_count > 0.05:
                findings.append(
                    Finding(
                        code="keyword_density",
                        severity="warning",
                        message=f"{term} exceeds five mentions and 5% of section words.",
                        section_key=section.key,
                    )
                )
    partial = {"next.js": "react", "postgresql": "sql", "typescript": "javascript"}
    for term in missing:
        if term in partial and contains(text, partial[term], aliases):
            findings.append(
                Finding(
                    code="partial_keyword",
                    severity="info",
                    message=(
                        f"{term}: related {partial[term]} is mentioned; "
                        "exact coverage remains missing."
                    ),
                )
            )
    for section, item in bullets:
        if re.search(r"\b(?:was|were|is|are|been)\s+\w+ed\b", item.text, re.I):
            findings.append(
                Finding(
                    code="passive_voice",
                    severity="info",
                    message="Possible passive voice; consider a direct sourced statement.",
                    section_key=section.key,
                    item_key=item.key,
                )
            )
    scores["action_verbs"] = round(100 * strong / len(bullets), 1) if bullets else 100
    scores["quantification"] = round(100 * quantified / len(bullets), 1) if bullets else 100
    for verb, count in verbs.items():
        if verb in VERBS and count > 3:
            findings.append(
                Finding(
                    code="repeated_verb",
                    severity="info",
                    message=f"{verb.title()} starts {count} bullets; consider varying the wording.",
                )
            )
    present = {s.type for s in visible if s.items}
    expected = {"experience", "education", "skills"}
    scores["structure"] = round(100 * len(present & expected) / 3, 1)
    for kind in sorted(expected - present):
        findings.append(
            Finding(
                code="structure",
                severity="info",
                message=f"No visible {kind} section. Include it when relevant.",
            )
        )
    for s in visible:
        dates = [i.facts.start_date for i in s.items if i.facts and i.facts.start_date]
        if dates != sorted(dates, reverse=True):
            findings.append(
                Finding(
                    code="chronology",
                    severity="info",
                    message="Consider reverse chronological order.",
                    section_key=s.key,
                )
            )
    rendered = resumes.render(document)
    pages = list(PdfReader(BytesIO(rendered.pdf)).pages)
    extracted = " ".join((p.extract_text() or "") for p in pages)

    def clean(value: str) -> str:
        return " ".join(value.split())

    expected_text = [
        document.header.name,
        *[s.title for s in visible],
        *[i.text for s in visible for i in s.items],
    ]
    parsed = VisibleText()
    parsed.feed(rendered.html)
    expected_text = parsed.segments
    position = 0
    absent = []
    for value in expected_text:
        offset = clean(extracted).find(clean(value), position)
        if offset == -1:
            absent.append(value)
        else:
            position = offset + len(clean(value))
    scores["parseability"] = 100 if not absent else 0
    if absent:
        findings.append(
            Finding(
                code="parseability",
                severity="warning",
                message="PDF extraction changed visible text or reading order. Inspect the PDF.",
            )
        )
    scores["length"] = 100 if rendered.page_count <= document.metadata.target_page_limit else 0
    if scores["length"] == 0:
        findings.append(
            Finding(
                code="page_limit",
                severity="warning",
                message=(
                    f"PDF has {rendered.page_count} pages; "
                    f"target is {document.metadata.target_page_limit}."
                ),
            )
        )
    if len(pages) > 1 and len(pages[-1].extract_text() or "") < 200:
        findings.append(
            Finding(
                code="sparse_page",
                severity="warning",
                message="Last page has little extracted text; visually inspect for orphan lines.",
            )
        )
    scores["readability"] = max(0, 100 - 10 * sum(f.code == "long_bullet" for f in findings))
    scores["formatting"] = 100
    weights = {
        "keywords": 35,
        "action_verbs": 10,
        "quantification": 10,
        "structure": 10,
        "parseability": 10,
        "length": 10,
        "readability": 10,
        "formatting": 5,
    }
    overall = sum(v * weights[k] for k, v in scores.items()) / sum(weights[k] for k in scores)
    return repo.save(
        db,
        owner,
        Report(
            id=uuid4(),
            version_id=version.id,
            analysis_id=data.analysis_id,
            created_at=utc_now(),
            engine_version=ENGINE_VERSION,
            overall_score=round(overall, 1),
            sub_scores=scores,
            matched_keywords=matched,
            missing_keywords=missing,
            findings=findings,
            page_count=rendered.page_count,
        ),
    )


def list_reports(db: Session, owner: UUID, identifier: UUID) -> list[Report]:
    resumes.get_version(db, owner, identifier)
    return repo.list_reports(db, owner, identifier)
