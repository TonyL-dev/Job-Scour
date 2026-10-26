import asyncio
import base64
import math
import time
from collections.abc import AsyncIterator
from contextlib import suppress
from io import BytesIO
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from pypdf import PdfReader
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.ai import repository as ai_repository
from app.ai.gateway import Gateway
from app.ai.generation import Writer, claim_check, numbers, source_text
from app.ai.retrieval import career_records, record_text, snapshot_digest
from app.career import service as career
from app.core.workspace import WorkspaceBarrier, bind, validate_session
from app.jobs import service as jobs
from app.resumes import generation_repository as repo
from app.resumes import repository as resume_repository
from app.resumes import service as resumes
from app.resumes.generation_schemas import (
    CommitReview,
    GenerateInput,
    GenerationRun,
    ReviewInput,
    RunEvent,
    Suggestion,
)
from app.resumes.schemas import (
    Item,
    MasterResume,
    Preview,
    ResumeDocument,
    SaveResume,
    Section,
    SourceRef,
)
from app.settings import service as settings
from app.settings.schemas import Task


def get(db: Session, owner: UUID, identifier: UUID) -> GenerationRun:
    row = repo.find(db, owner, identifier)
    if row is None:
        raise HTTPException(404, "Generation run not found")
    return repo.read(db, row)


def list_runs(db: Session, owner: UUID) -> list[GenerationRun]:
    return repo.list_runs(db, owner)


def reorder_unlocked(items: list[Item], order: list[UUID]) -> list[Item]:
    # Sort into unlocked slots only; protected items keep their exact positions.
    positions = {key: index for index, key in enumerate(order)}
    unlocked = iter(
        sorted((i for i in items if not i.locked), key=lambda i: positions.get(i.key, len(order)))
    )
    return [item if item.locked else next(unlocked) for item in items]


def item_budget(content: ResumeDocument) -> int:
    # This bounds initial candidate work, not the final page count. Fitting later
    # measures actual Chromium PDFs before removing or condensing unlocked content.
    from app.rendering.service import template_for

    template = template_for(content)
    style = template.default_styles.model_dump()
    style.update(content.metadata.style_overrides.model_dump(exclude_none=True))
    font = float(style["font_size_pt"] or 11)
    height = float(style["line_height"] or 1.3)
    margin = float(style["margin_mm"] or 18)
    chars_per_line = max(30, (210 - margin * 2) * 2.83465 / (font * 0.52))
    lines_per_page = max(10, (297 - margin * 2 - 45) / (font * 0.3528 * height))
    lines_per_item = math.ceil(350 / chars_per_line) + 2
    return min(
        24, max(4, int(lines_per_page * content.metadata.target_page_limit / lines_per_item))
    )


def assemble(run: GenerationRun, review: ReviewInput) -> ResumeDocument:
    if run.status in {"running", "queued"}:
        raise HTTPException(409, "Wait for generation or cancel before reviewing")
    if review.expected_revision != run.review_revision:
        raise HTTPException(409, "Review changed elsewhere. Reload before continuing.")
    choices = {d.suggestion_id: d for d in review.decisions}
    if len(choices) != len(review.decisions) or set(choices) - {s.id for s in run.suggestions}:
        raise HTTPException(422, "Unknown or duplicate suggestion decision")
    result = run.base.model_copy(deep=True)
    ordering: dict[UUID, list[UUID]] = {}
    for suggestion in run.suggestions:
        decision = choices.get(suggestion.id)
        if decision is None or decision.action == "reject":
            continue
        section = next(s for s in result.sections if s.key == suggestion.section_key)
        original = next((i for i in section.items if i.key == suggestion.item_key), None)
        if section.locked or (original and original.locked):
            raise HTTPException(422, "Protected content cannot be changed by suggestions")
        if suggestion.order_keys is not None:
            if decision.action != "accept":
                raise HTTPException(422, "Ordering suggestions can be accepted or rejected")
            ordering[section.key] = suggestion.order_keys
            continue
        proposed = suggestion.proposed.model_copy(deep=True) if suggestion.proposed else None
        if decision.action == "accept" and suggestion.verification != "supported":
            raise HTTPException(422, "Unsupported changes require a sourced manual edit")
        if decision.action == "edit":
            if proposed is None:
                if original is None:
                    raise HTTPException(422, "Cannot edit an absent item")
                proposed = original.model_copy(deep=True)
            proposed.text = decision.text or ""
            proposed.origin = "user"
        index = next(
            (n for n, i in enumerate(section.items) if i.key == suggestion.item_key),
            len(section.items),
        )
        section.items = [i for i in section.items if i.key != suggestion.item_key]
        if proposed:
            section.items.insert(index, proposed)
    for section in result.sections:
        if section.key in ordering:
            section.items = reorder_unlocked(section.items, ordering[section.key])
    targets: dict[str, Section | Item] = {str(s.key): s for s in result.sections}
    targets.update({str(i.key): i for s in result.sections for i in s.items})
    if set(review.locks) - set(targets):
        raise HTTPException(422, "Unknown review lock target")
    for key, locked in review.locks.items():
        targets[key].locked = locked
    result.metadata.job_description_id = run.request.job_id
    if run.request.preset == "fit":
        result.metadata.target_page_limit = min(2, result.metadata.target_page_limit)
    # Presentation changes are consented run inputs and shown in the review preview.
    if run.proposed and run.request.allow_layout_adjustments:
        result.metadata.style_overrides = run.proposed.metadata.style_overrides.model_copy(
            deep=True
        )
    return result


def review_content(db: Session, owner: UUID, identifier: UUID, data: ReviewInput) -> ResumeDocument:
    run = get(db, owner, identifier)
    if (
        run.provenance.get("career_snapshot")
        and snapshot_digest(career_records(db, owner)) != run.provenance["career_snapshot"]
    ):
        raise HTTPException(
            409, "Career sources changed since generation. Generate again before review."
        )
    result = assemble(run, data)
    accepted = {d.suggestion_id for d in data.decisions if d.action == "accept"}
    for suggestion in run.suggestions:
        if suggestion.id not in accepted or suggestion.proposed is None:
            continue
        factual_sources: dict[UUID, str] = {}
        for ref in suggestion.proposed.source_refs:
            record = career.get(db, owner, ref.entity_type, ref.entity_id)
            factual_sources[ref.entity_id] = source_text(record)
            current = (
                source_text(record)
                if run.provenance.get("source_context_version") == "facts.v1"
                else record_text(record)
            )
            if suggestion.sources.get(str(ref.entity_id)) != current:
                raise HTTPException(409, "Cited evidence changed since generation. Generate again.")
        if claim_check(
            suggestion.proposed.text,
            factual_sources,
            [ref.entity_id for ref in suggestion.proposed.source_refs],
            [],
        ):
            raise HTTPException(
                422,
                "Proposal fails current claim checks. Regenerate or confirm a sourced manual edit.",
            )
    jobs.get(db, owner, run.request.job_id)
    return resumes.validate(db, owner, result, allow_ai=True)


def save_review(db: Session, owner: UUID, identifier: UUID, data: ReviewInput) -> GenerationRun:
    review_content(db, owner, identifier, data)
    if not repo.record_review(
        db,
        owner,
        identifier,
        data.expected_revision,
        [d.model_dump(mode="json") for d in data.decisions],
        data.locks,
    ):
        db.rollback()
        raise HTTPException(409, "Review changed elsewhere. Reload.")
    db.commit()
    return get(db, owner, identifier)


def commit(db: Session, owner: UUID, identifier: UUID, data: CommitReview) -> MasterResume:
    run = get(db, owner, identifier)
    if run.saved_resume_id:
        saved = resumes.get(db, owner, run.saved_resume_id)
        if run.saved_version_id:
            version = resumes.get_version(db, owner, run.saved_version_id)
            return saved.model_copy(
                update={
                    "content": version.content,
                    "version_number": version.version_number,
                    "updated_at": version.created_at,
                }
            )
        return saved
    content = review_content(db, owner, identifier, data)
    if not repo.record_review(
        db,
        owner,
        identifier,
        data.expected_revision,
        [d.model_dump(mode="json") for d in data.decisions],
        data.locks,
    ):
        db.rollback()
        raise HTTPException(409, "Review changed elsewhere. Reload.")
    # The review CAS and new immutable resume are committed in the same transaction.
    result = resume_repository.save(
        db,
        owner,
        SaveResume(title=data.title, content=content),
        None,
        kind="tailored",
        commit=False,
        change_kind="ai",
        parent_document_id=run.request.master_id,
    )
    assert result is not None
    version = resume_repository.versions(db, owner, result.id)[0]
    repo.link_saved_resume(db, owner, identifier, result.id, version.id)
    return result


async def preview(db: Session, owner: UUID, identifier: UUID, data: ReviewInput) -> Preview:
    content = review_content(db, owner, identifier, data)
    rendered = await asyncio.to_thread(resumes.render, content)
    warnings = []
    if rendered.page_count > content.metadata.target_page_limit:
        warnings.append(
            "Your review choices exceed the page target. Reject more items or run Fit to 2 pages."
        )
    return Preview(
        html=rendered.html,
        pdf_base64=base64.b64encode(rendered.pdf).decode(),
        page_count=rendered.page_count,
        html_hash=rendered.html_hash,
        warnings=warnings,
    )


PRESETS = {
    "tailor": "Emphasize relevant evidence without adding facts.",
    "rewrite_summary": "Rewrite the summary from selected evidence.",
    "quantify": "Use only metrics explicitly stored in sources; never invent numbers.",
    "concise": "Make the text more concise.",
    "senior": "Use direct language without inflating seniority, leadership, or scope.",
    "technical": "Emphasize only technical details explicitly supported by sources.",
    "fit": "Keep facts and metrics while shortening to fit two pages.",
}


async def pipeline(db: Session, owner: UUID, run: GenerationRun, gateway: Gateway) -> None:
    started = time.monotonic()
    sequence = 0
    last_stage = ""

    async def stage(text: str) -> None:
        nonlocal sequence, last_stage
        if text == last_stage:
            return
        last_stage = text
        sequence += 1
        repo.progress(
            db,
            owner,
            run.id,
            RunEvent(
                sequence=sequence, stage=text, elapsed_seconds=round(time.monotonic() - started, 2)
            ),
        )

    data = run.request
    tasks: list[Task] = ["ranking", "rewriting", "summary", "verification", "condensing"]
    writer = Writer(gateway, {task: settings.resolve(db, owner, task) for task in tasks})
    for prompt in writer.prompts.values():
        ai_repository.seed_prompt(db, owner, prompt)
    analysis = await jobs.analyze(db, owner, data.job_id, gateway, data.use_embeddings, stage)
    records = career_records(db, owner)
    digest = snapshot_digest(records)
    writer.provenance["career_snapshot"] = digest
    writer.provenance["job_analysis"] = f"{analysis.id}:{analysis.model}:{analysis.prompt_version}"
    sources = {r.id: source_text(r) for r in records}
    source_types = {r.id: r.data.type for r in records}
    scores = {m.source_ref.entity_id: m.score for m in analysis.match.items}
    content = resumes.validate(db, owner, run.base, allow_ai=True)
    content.metadata.job_description_id = data.job_id
    if data.preset == "fit":
        content.metadata.target_page_limit = min(2, content.metadata.target_page_limit)
    # Summary uses selected visible content, including protected/non-retrieval categories.
    for section in content.sections:
        for item in section.items:
            for ref in item.source_refs:
                if ref.entity_id not in sources:
                    record = career.get(db, owner, ref.entity_type, ref.entity_id)
                    sources[ref.entity_id] = source_text(record)
                    source_types[ref.entity_id] = ref.entity_type
    suggestions: list[Suggestion] = []
    warnings = list(analysis.match.warnings)
    terms = list(
        {
            r.term
            for r in [
                *analysis.analysis.required_skills,
                *analysis.analysis.preferred_skills,
                *analysis.analysis.technologies,
                *analysis.analysis.keywords,
            ]
        }
    )
    terms += [r.data.name for r in records if r.data.type == "skill"]
    scope_sections = set(data.section_keys)
    scope_items = set(data.item_keys)
    partial = bool(scope_sections or scope_items or data.preset == "rewrite_summary")

    def editable(section_key: UUID, item: Item | None = None) -> bool:
        section = next(s for s in content.sections if s.key == section_key)
        if section.locked or not section.visible or (item and item.locked):
            return False
        if data.preset == "rewrite_summary":
            return section.type == "summary"
        return (
            not partial
            or section_key in scope_sections
            or (item is not None and item.key in scope_items)
        )

    await stage("Ranking sourced candidates")
    budget = item_budget(content)
    writer.provenance["initial_item_budget"] = str(budget)
    candidates = [
        m
        for m in analysis.match.items[:24]
        if m.source_ref.entity_type in {"achievement", "project", "skill"}
    ]
    selected_ids: list[UUID] = []
    if not partial:
        selected = await writer.rank(
            {
                "requirements": [k.term for k in analysis.analysis.keywords],
                "maximum_count": budget,
                "candidates": [
                    {
                        "source_id": str(m.source_ref.entity_id),
                        "text": sources[m.source_ref.entity_id][:700],
                        "score": m.score,
                    }
                    for m in candidates
                ],
            }
        )
        candidate_ids = {m.source_ref.entity_id for m in candidates}
        selected_ids = [c.source_id for c in selected.choices]
        if len(selected_ids) != len(set(selected_ids)) or any(
            i not in candidate_ids for i in selected_ids
        ):
            raise HTTPException(502, "Ranking returned unavailable or duplicate career sources")
        selected_ids = selected_ids[:budget]
        writer.provenance["ranking_selection"] = selected.model_dump_json()
    for section in content.sections:
        if partial or not editable(section.key):
            continue
        for identifier in selected_ids:
            kind = source_types[identifier]
            record = next(r for r in records if r.id == identifier)
            target = (
                "skills"
                if kind == "skill"
                else "projects"
                if kind == "project"
                or (record.data.type == "achievement" and record.data.project_id)
                else "experience"
            )
            if section.type != target or any(
                identifier == ref.entity_id
                for s in content.sections
                for i in s.items
                for ref in i.source_refs
            ):
                continue
            ref = SourceRef(entity_type=kind, entity_id=identifier)
            # New candidates are rewritten and verified before any inclusion.
            section.items.append(
                Item(key=uuid4(), text=sources[identifier][:1500], origin="user", source_refs=[ref])
            )
    base_items = {i.key: i for s in run.base.sections for i in s.items}
    if not partial:
        eligible = [
            (s, i)
            for s in content.sections
            if s.type in {"experience", "projects"}
            for i in s.items
            if editable(s.key, i) and i.source_refs
        ]
        eligible.sort(
            key=lambda pair: (
                -max((scores.get(ref.entity_id, 0) for ref in pair[1].source_refs), default=0),
                str(pair[1].key),
            )
        )
        for section, item in eligible[budget:]:
            section.items = [i for i in section.items if i.key != item.key]
            if item.key in base_items:
                suggestions.append(
                    Suggestion(
                        id=uuid4(),
                        section_key=section.key,
                        item_key=item.key,
                        original=base_items[item.key],
                        proposed=None,
                        verification="supported",
                        reason="Excluded from the template's initial relevance/line budget",
                    )
                )

    async def propose(
        section_key: UUID, item: Item, task: Task = "rewriting", max_chars: int = 350
    ) -> None:
        nonlocal content
        allowed = {
            ref.entity_id: sources[ref.entity_id]
            for ref in item.source_refs
            if ref.entity_id in sources
        }
        # Other stored categories used by a master remain valid, bounded sources.
        for ref in item.source_refs:
            if ref.entity_id not in allowed:
                allowed[ref.entity_id] = source_text(
                    career.get(db, owner, ref.entity_type, ref.entity_id)
                )
        section = next(s for s in content.sections if s.key == section_key)
        if task == "summary":
            allowed = {
                ref.entity_id: sources[ref.entity_id]
                for s in content.sections
                if s.visible and s.type != "summary"
                for i in s.items
                for ref in i.source_refs
                if ref.entity_id in sources
            }
            allowed = dict(list(allowed.items())[:10])
        if not allowed:
            warnings.append("Unsourced manual text was preserved and excluded from AI rewriting.")
            if item.key not in base_items:
                section.items = [i for i in section.items if i.key != item.key]
            return
        await stage(f"Rewriting {section.title}")
        rewritten = await writer.rewrite(
            {
                "sources": {str(k): v for k, v in allowed.items()},
                "original": item.text if item.key in base_items else "",
                "keywords": [
                    t for t in terms if any(t.casefold() in v.casefold() for v in allowed.values())
                ][:20],
                "character_budget": max_chars,
                "style_instruction": PRESETS[data.preset]
                + " "
                + data.instruction
                + (
                    " Use one sentence on one line, at most 500 characters."
                    if item.experience_summary
                    else ""
                ),
            },
            task,
        )
        failure = claim_check(rewritten.text, allowed, rewritten.source_ids, terms)
        if task == "condensing" and (
            len(rewritten.text) > max_chars or numbers(item.text) - numbers(rewritten.text)
        ):
            failure = "Rejected: condensation exceeded its budget or removed a metric."
        refs = [
            SourceRef(
                entity_type=next(
                    (ref.entity_type for ref in item.source_refs if ref.entity_id == i),
                    source_types.get(i, "achievement"),
                ),
                entity_id=i,
            )
            for i in dict.fromkeys(rewritten.source_ids)
            if i in allowed
        ]
        try:
            proposed = (
                Item(
                    key=item.key,
                    text=rewritten.text,
                    origin="ai",
                    source_refs=refs,
                    experience_summary=item.experience_summary,
                )
                if refs
                else None
            )
        except ValidationError:
            if not item.experience_summary:
                raise
            proposed = None
            failure = "Rejected: experience summary must be one sentence, at most 500 characters."
        await stage(f"Verifying {section.title}")
        verified = (
            await writer.verify(
                rewritten.text, {i: allowed[i] for i in rewritten.source_ids if i in allowed}
            )
            if not failure
            else None
        )
        status = (
            "unsupported"
            if failure or proposed is None
            else verified.status
            if verified
            else "unsupported"
        )
        reason = failure or (verified.reason if verified else "No valid cited source")
        suggestion = Suggestion(
            id=uuid4(),
            section_key=section_key,
            item_key=item.key,
            original=base_items.get(item.key),
            proposed=proposed,
            verification=status,
            reason=reason,
            sources={str(k): v for k, v in allowed.items() if k in rewritten.source_ids},
            rejected_text=rewritten.text if proposed is None else None,
        )
        # Condensation replaces a prior proposal rather than producing competing patches.
        old = next((s for s in suggestions if s.item_key == item.key), None)
        if old and task == "condensing":
            if status != "supported":
                return
            suggestions.remove(old)
        suggestions.append(suggestion)
        if status == "supported" and proposed:
            section.items = [proposed if i.key == item.key else i for i in section.items]
        elif item.key not in base_items:
            section.items = [i for i in section.items if i.key != item.key]

    for section in content.sections:
        if section.type == "summary":
            continue
        for item in list(section.items):
            if not editable(section.key, item):
                continue
            if section.type == "skills":
                if len(item.source_refs) == 1 and item.source_refs[0].entity_id in sources:
                    record = next(r for r in records if r.id == item.source_refs[0].entity_id)
                    if record.data.type == "skill":
                        item.text = record.data.name
                        item.origin = "ai"
                        if item.key not in base_items or item.text != base_items[item.key].text:
                            suggestions.append(
                                Suggestion(
                                    id=uuid4(),
                                    section_key=section.key,
                                    item_key=item.key,
                                    original=base_items.get(item.key),
                                    proposed=item.model_copy(deep=True),
                                    verification="supported",
                                    reason="Skill name copied from the career library",
                                    sources={str(record.id): sources[record.id]},
                                )
                            )
            else:
                await propose(section.key, item)
            repo.checkpoint(db, owner, run.id, content, suggestions, writer.provenance)
    for section in content.sections:
        if section.type == "skills" and not partial and editable(section.key):
            before = [i.key for i in section.items]
            order = [
                i.key
                for i in sorted(
                    section.items,
                    key=lambda item: (
                        -max((scores.get(ref.entity_id, 0) for ref in item.source_refs), default=0)
                    ),
                )
            ]
            section.items = reorder_unlocked(section.items, order)
            if [i.key for i in section.items] != before:
                suggestions.append(
                    Suggestion(
                        id=uuid4(),
                        section_key=section.key,
                        item_key=section.key,
                        original=None,
                        proposed=None,
                        verification="supported",
                        reason="Order stored skills by relevance; preserve protected positions",
                        order_keys=[i.key for i in section.items],
                    )
                )
                repo.checkpoint(db, owner, run.id, content, suggestions, writer.provenance)
        if section.type != "summary" or not (
            any(editable(section.key, i) for i in section.items)
            if section.items
            else editable(section.key)
        ):
            continue
        if not section.items and not scope_items:
            section.items.append(Item(key=uuid4(), text="Summary", origin="user", source_refs=[]))
        for item in list(section.items):
            if editable(section.key, item):
                await propose(section.key, item, "summary", 500)
                repo.checkpoint(db, owner, run.id, content, suggestions, writer.provenance)
    content = resumes.validate(db, owner, content, allow_ai=True)

    def priority(item: Item) -> float:
        return max((scores.get(r.entity_id, 0) for r in item.source_refs), default=0)

    async def measure() -> int:
        await stage("Measuring actual PDF pages")
        rendered = await asyncio.to_thread(resumes.render, content.model_copy(deep=True))
        pdf_pages = PdfReader(BytesIO(rendered.pdf)).pages
        writer.provenance["last_page_text_characters"] = str(
            len(pdf_pages[-1].extract_text().strip())
        )
        return rendered.page_count

    pages = await measure()
    limit = (
        min(2, content.metadata.target_page_limit)
        if data.preset == "fit"
        else content.metadata.target_page_limit
    )
    # Ordered, bounded fitting. No protected item is dropped or sent for modification.
    removable = [
        (s, i)
        for s in content.sections
        if s.type in {"experience", "projects"}
        for i in s.items
        if editable(s.key, i)
    ]
    removable.sort(key=lambda pair: (priority(pair[1]), str(pair[1].key)))
    reserve = max(2, limit * 2)
    for section, item in removable:
        if (
            pages <= limit
            or len([i for s in content.sections if s.visible for i in s.items]) <= reserve
        ):
            break
        section.items = [i for i in section.items if i.key != item.key]
        suggestions = [s for s in suggestions if s.item_key != item.key]
        if item.key in base_items:
            suggestions.append(
                Suggestion(
                    id=uuid4(),
                    section_key=section.key,
                    item_key=item.key,
                    original=base_items[item.key],
                    proposed=None,
                    verification="supported",
                    reason="Removed lowest relevance unlocked item to fit the page target",
                )
            )
        pages = await measure()
    if pages > limit:
        # Remove whole low-relevance older fact groups only after individual bullets.
        groups: list[tuple[float, str, UUID, list[Item]]] = []
        for section in content.sections:
            if section.type not in {"experience", "projects"}:
                continue
            grouped: dict[str, list[Item]] = {}
            for item in section.items:
                key = item.facts.model_dump_json() if item.facts else str(item.key)
                grouped.setdefault(key, []).append(item)
            for items in grouped.values():
                if all(editable(section.key, i) for i in items):
                    dates = [
                        str(i.facts.end_date or i.facts.start_date or "9999")
                        for i in items
                        if i.facts
                    ]
                    groups.append(
                        (
                            max(priority(i) for i in items),
                            min(dates, default="9999"),
                            section.key,
                            items,
                        )
                    )
        for _, _, section_key, items in sorted(groups, key=lambda g: (g[0], g[1], str(g[2]))):
            if pages <= limit or sum(len(s.items) for s in content.sections) <= len(items):
                break
            section = next(s for s in content.sections if s.key == section_key)
            for item in items:
                section.items = [i for i in section.items if i.key != item.key]
                suggestions = [s for s in suggestions if s.item_key != item.key]
                if item.key in base_items:
                    suggestions.append(
                        Suggestion(
                            id=uuid4(),
                            section_key=section_key,
                            item_key=item.key,
                            original=base_items[item.key],
                            proposed=None,
                            verification="supported",
                            reason="Removed an older, lower relevance experience/project group",
                        )
                    )
            pages = await measure()
    if pages > limit:
        for section in content.sections:
            for item in sorted(list(section.items), key=lambda i: -len(i.text)):
                if pages <= limit:
                    break
                if editable(section.key, item) and len(item.text) > 180:
                    await propose(section.key, item, "condensing", max(120, len(item.text) // 2))
                    content = resumes.validate(db, owner, content, allow_ai=True)
                    pages = await measure()
    if pages > limit and data.allow_layout_adjustments:
        from app.rendering.service import template_for

        defaults = template_for(content).default_styles
        style = content.metadata.style_overrides
        spacing = (
            style.section_spacing_mm
            if style.section_spacing_mm is not None
            else defaults.section_spacing_mm or 5
        )
        font = style.font_size_pt if style.font_size_pt is not None else defaults.font_size_pt or 11
        style.section_spacing_mm = min(spacing, max(2, spacing - 1))
        style.font_size_pt = min(font, max(10, font - 0.5))
        pages = await measure()
        warnings.append(
            "Consented layout fitting reduced spacing/font size within template bounds."
        )
    if pages > limit:
        warnings.append(
            "Page target could not be met without changing protected content. "
            "Review locks and retry."
        )
    if pages > 1 and int(writer.provenance.get("last_page_text_characters", "0")) < 200:
        warnings.append(
            "The last page contains little text. Inspect the PDF for orphan lines before saving."
        )
    if snapshot_digest(career_records(db, owner)) != digest:
        raise HTTPException(
            409, "Career sources changed during generation. Retry before applying suggestions."
        )
    content = resumes.validate(db, owner, content, allow_ai=True)
    repo.checkpoint(db, owner, run.id, content, suggestions, writer.provenance)
    repo.finish(db, owner, run.id, "succeeded", pages=pages, warnings=warnings)


class RunManager:
    """One local worker with bounded queued tasks; persisted runs survive browser disconnects."""

    def __init__(
        self, engine: Engine, gateway: Gateway, barrier: WorkspaceBarrier | None = None
    ) -> None:
        self.engine = engine
        self.barrier = barrier
        self.gateway = gateway
        self.tasks: dict[UUID, asyncio.Task[None]] = {}
        self.slot = asyncio.Semaphore(1)
        repo.recover(engine)

    def start(self, db: Session, owner: UUID, data: GenerateInput) -> GenerationRun:
        if len(self.tasks) >= 4:
            raise HTTPException(429, "Generation queue is full. Wait or cancel a run.")
        master = resumes.get(db, owner, data.master_id)
        if master.kind != "master":
            raise HTTPException(422, "Choose a master resume")
        jobs.get(db, owner, data.job_id)
        base = master.content
        if data.parent_run_id:
            parent = get(db, owner, data.parent_run_id)
            if parent.request.master_id != data.master_id or parent.request.job_id != data.job_id:
                raise HTTPException(422, "Regeneration must keep the same master and job")
            base = assemble(
                parent,
                ReviewInput(
                    decisions=parent.decisions,
                    locks=parent.locks,
                    expected_revision=parent.review_revision,
                ),
            )
        sections = {s.key for s in base.sections}
        items = {i.key for s in base.sections for i in s.items}
        if set(data.section_keys) - sections or set(data.item_keys) - items:
            raise HTTPException(422, "Unknown regeneration scope")
        base = resumes.validate(db, owner, base, allow_ai=True)
        for task in (
            "job_analysis",
            "ranking",
            "rewriting",
            "summary",
            "verification",
            "condensing",
        ):
            settings.resolve(db, owner, task)
        run = repo.create(db, owner, data, base)
        self.tasks[run.id] = asyncio.create_task(self.execute(owner, run))
        return run

    async def execute(self, owner: UUID, run: GenerationRun) -> None:
        try:
            async with self.slot:
                with Session(self.engine) as db:
                    if self.barrier:
                        bind(db, self.barrier)
                    await pipeline(db, owner, run, self.gateway)
        except asyncio.CancelledError:
            with Session(self.engine) as db:
                repo.finish(
                    db,
                    owner,
                    run.id,
                    "cancelled",
                    error="Generation cancelled. Partial suggestions are preserved.",
                )
        except Exception as error:
            detail = (
                str(error.detail)
                if isinstance(error, HTTPException)
                else "Generation failed. Check local model and renderer settings, then retry."
            )
            with Session(self.engine) as db:
                repo.finish(db, owner, run.id, "failed", error=detail)
        finally:
            self.tasks.pop(run.id, None)

    async def cancel(self, db: Session, owner: UUID, identifier: UUID) -> GenerationRun:
        run = get(db, owner, identifier)
        task = self.tasks.get(identifier)
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            # A task cancelled before first execution still needs a durable status.
            self.tasks.pop(identifier, None)
            repo.finish(
                db,
                owner,
                identifier,
                "cancelled",
                error="Generation cancelled. Partial suggestions are preserved.",
            )
        return get(db, owner, identifier) if task else run

    async def close(self) -> None:
        tasks = list(self.tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def events(
    engine: Engine,
    owner: UUID,
    identifier: UUID,
    after: int,
    barrier: WorkspaceBarrier | None = None,
    epoch: int | None = None,
) -> AsyncIterator[str]:
    last = after
    # SSE only observes persisted progress. Disconnecting this reader leaves the
    # worker running; sequence IDs allow a reconnect to skip already-seen events.
    while True:
        if barrier and epoch is not None and barrier.epoch != epoch:
            return
        with Session(engine) as db:
            if barrier:
                bind(db, barrier, epoch)
            validate_session(db)
            run = get(db, owner, identifier)
        for event in run.events:
            if event.sequence > last:
                if barrier and epoch is not None and barrier.epoch != epoch:
                    return
                last = event.sequence
                yield f"id: {last}\nevent: progress\ndata: {event.model_dump_json()}\n\n"
        if barrier and epoch is not None and barrier.epoch != epoch:
            return
        if run.status not in {"queued", "running"}:
            yield f"event: result\ndata: {run.model_dump_json()}\n\n"
            return
        yield ": heartbeat\n\n"
        await asyncio.sleep(1)
