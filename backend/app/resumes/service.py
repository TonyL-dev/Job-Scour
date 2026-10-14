import base64
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.generation import claim_check, source_text
from app.career import service as career
from app.rendering import service as rendering
from app.resumes import repository, schemas
from app.resumes.schemas import (
    DisplayFacts,
    MasterResume,
    Preview,
    ResumeDocument,
    SaveResume,
    TemplateInfo,
)

SECTION_SOURCES: dict[str, set[str]] = {
    "experience": {"experience", "achievement"},
    "projects": {"project", "achievement"},
    "skills": {"skill"},
    "education": {"education", "course"},
    "certifications": {"certification"},
    "volunteer": {"volunteer_experience"},
    "awards": {"award"},
    "publications": {"publication"},
    "custom": {"custom_entry"},
}


def templates(session: Session | None = None, owner: UUID | None = None) -> list[TemplateInfo]:
    from app.templates import service as custom

    return [
        *rendering.TEMPLATES,
        *(
            custom.template_infos(session, owner)
            if session is not None and owner is not None
            else []
        ),
    ]


def export_docx(session: Session, owner: UUID, identifier: UUID) -> bytes:
    from app.rendering.docx import export

    return export(get_version(session, owner, identifier).content)


def validate(
    session: Session,
    owner: UUID,
    content: ResumeDocument,
    *,
    allow_ai: bool = False,
    protect_ai_locks: bool = True,
) -> ResumeDocument:
    result = content.model_copy(deep=True)
    from app.templates import service as custom

    if result.metadata.template_id in {t.id for t in rendering.TEMPLATES}:
        result.metadata.custom_template = None
    else:
        result.metadata.custom_template = custom.snapshot(
            session, owner, result.metadata.template_id
        )
    if result.metadata.job_description_id is not None and not allow_ai:
        raise HTTPException(422, "Use generation to link a tailored resume to a job")
    for section in result.sections:
        for item in section.items:
            original = item.model_copy(deep=True)
            if item.origin != "user" and not allow_ai:
                raise HTTPException(422, "Use generation review to save AI suggestions")
            item.facts = None
            for ref in item.source_refs:
                if (
                    section.type != "summary"
                    and ref.entity_type not in SECTION_SOURCES[section.type]
                ):
                    raise HTTPException(422, "Source type does not match section")
                record = career.get(session, owner, ref.entity_type, ref.entity_id)
                data = record.data
                # Verify active parent chains too (including achievements and courses).
                for key, kind in career.RELATIONS.items():
                    if (parent_id := getattr(data, key, None)) is not None:
                        career.get(session, owner, kind, parent_id)  # type: ignore[arg-type]
                if section.type == "summary":
                    continue
                fact_source = data
                if data.type == "achievement" and section.type in {"experience", "projects"}:
                    parent_kind = "experience" if section.type == "experience" else "project"
                    parent_id = getattr(data, parent_kind + "_id")
                    if parent_id is None:
                        raise HTTPException(422, "Achievement parent does not match section")
                    fact_source = career.get(session, owner, parent_kind, parent_id).data  # type: ignore[arg-type]
                values = fact_source.model_dump()
                facts = DisplayFacts(
                    employer=values.get("company", values.get("organization")),
                    title=values.get("job_title", values.get("title", values.get("role"))),
                    institution=values.get("institution"),
                    degree=values.get("degree"),
                    location=values.get("location"),
                    start_date=values.get("start_date"),
                    end_date=values.get("end_date"),
                    current=values.get("current", False),
                )
                if fact_source.type == "project":
                    facts.title = fact_source.name
                    if fact_source.role:
                        facts.title += " · " + fact_source.role
                if item.facts is not None and item.facts != facts:
                    raise HTTPException(
                        422, "One item cannot combine different employers, titles, or dates"
                    )
                item.facts = facts
            if (
                allow_ai
                and protect_ai_locks
                and (section.locked or original.locked)
                and original.facts is not None
                and item != original
            ):
                raise HTTPException(
                    409, "Protected source facts changed. Review the master before generation."
                )
    return result


def get(session: Session, owner: UUID, identifier: UUID) -> MasterResume:
    row = repository.find(session, owner, identifier)
    if row is None:
        raise HTTPException(404, "Resume not found")
    return repository.read(session, row)


def list_resumes(session: Session, owner: UUID) -> list[MasterResume]:
    return repository.list_resumes(session, owner)


def save(
    session: Session, owner: UUID, data: SaveResume, identifier: UUID | None = None
) -> MasterResume:
    existing = get(session, owner, identifier) if identifier else None
    if existing:
        if existing.version_number != data.expected_version:
            raise HTTPException(409, "Resume changed elsewhere. Reload before saving.")
        if existing.kind == "tailored" and data.gold_standard:
            raise HTTPException(422, "Only a master can be the gold standard")
        validated_content = manual_content(session, owner, existing, data.content)
    else:
        if data.expected_version != 0:
            raise HTTPException(409, "New resumes require expected_version 0")
        validated_content = validate(session, owner, data.content)
    validated = data.model_copy(update={"content": validated_content})
    if (
        existing
        and existing.title == validated.title
        and existing.gold_standard == validated.gold_standard
        and existing.content == validated.content
    ):
        return existing
    try:
        result = repository.save(session, owner, validated, identifier)
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(409, "Resume changed elsewhere. Reload before saving.") from error
    if result is None:
        raise HTTPException(409, "Resume changed elsewhere. Reload before saving.")
    return result


def manual_content(
    session: Session, owner: UUID, existing: MasterResume, content: ResumeDocument
) -> ResumeDocument:
    if content.metadata.job_description_id != existing.content.metadata.job_description_id:
        raise HTTPException(422, "Manual edits must preserve the linked job")
    original = {i.key: i for section in existing.content.sections for i in section.items}
    for section in content.sections:
        for item in section.items:
            if item.origin == "ai":
                previous = original.get(item.key)
                if (
                    previous is None
                    or previous.origin != "ai"
                    or (previous.text, previous.source_refs, previous.facts)
                    != (item.text, item.source_refs, item.facts)
                ):
                    raise HTTPException(
                        422,
                        "New AI claims require generation review. "
                        "Mark manual edits as user content.",
                    )
                sources = {
                    ref.entity_id: source_text(
                        career.get(session, owner, ref.entity_type, ref.entity_id)
                    )
                    for ref in item.source_refs
                }
                if claim_check(item.text, sources, [ref.entity_id for ref in item.source_refs], []):
                    raise HTTPException(
                        409,
                        "Stored AI text no longer passes current evidence checks. "
                        "Regenerate or confirm a sourced manual edit.",
                    )
    return validate(session, owner, content, allow_ai=True, protect_ai_locks=False)


def render(content: ResumeDocument) -> rendering.Rendered:
    try:
        return rendering.render(content)
    except rendering.RendererBusy as error:
        raise HTTPException(503, "PDF renderer busy. Retry shortly.") from error
    except rendering.RendererError as error:
        raise HTTPException(
            503,
            "PDF renderer unavailable. "
            "Install Chromium with python -m playwright install chromium.",
        ) from error


def preview(session: Session, owner: UUID, content: ResumeDocument) -> Preview:
    validated = validate(session, owner, content)
    rendered = render(validated)
    warnings = []
    if rendered.page_count > content.metadata.target_page_limit:
        warnings.append(
            f"Resume is {rendered.page_count} pages; "
            f"target is {content.metadata.target_page_limit}."
        )
    if any(not item.source_refs for section in validated.sections for item in section.items):
        warnings.append("Manual text without sources is unverified.")
    return Preview(
        html=rendered.html,
        pdf_base64=base64.b64encode(rendered.pdf).decode("ascii"),
        page_count=rendered.page_count,
        html_hash=rendered.html_hash,
        warnings=warnings,
    )


def history(session: Session, owner: UUID, identifier: UUID) -> list[schemas.ResumeVersion]:
    get(session, owner, identifier)
    return repository.versions(session, owner, identifier)


def get_version(session: Session, owner: UUID, identifier: UUID) -> schemas.ResumeVersion:
    result = repository.version(session, owner, identifier)
    if result is None:
        raise HTTPException(404, "Resume version not found")
    return result


def version_action(
    session: Session, owner: UUID, identifier: UUID, data: schemas.VersionAction, duplicate: bool
) -> MasterResume:
    version = get_version(session, owner, identifier)
    current = get(session, owner, version.document_id)
    if current.version_number != data.expected_version:
        raise HTTPException(
            409, "Resume changed elsewhere. Reload before restoring or duplicating."
        )
    # Restore/duplicate copy the immutable historical snapshot, including retired facts.
    # New edits still require active sources; this action never rewrites stored evidence.
    saved = repository.save(
        session,
        owner,
        SaveResume(
            title=data.title or (current.title + " (copy)" if duplicate else current.title),
            gold_standard=False if duplicate else current.gold_standard,
            expected_version=0 if duplicate else data.expected_version,
            content=version.content,
        ),
        None if duplicate else current.id,
        kind=current.kind,
        parent_document_id=current.id if duplicate else None,
        restored_from_version_id=version.id,
        change_kind="duplicate" if duplicate else "restore",
    )
    if saved is None:
        raise HTTPException(409, "Resume changed elsewhere")
    return saved


def manual_preview(
    session: Session, owner: UUID, identifier: UUID, content: ResumeDocument
) -> Preview:
    validated = manual_content(session, owner, get(session, owner, identifier), content)
    rendered = render(validated)
    return Preview(
        html=rendered.html,
        pdf_base64=base64.b64encode(rendered.pdf).decode("ascii"),
        page_count=rendered.page_count,
        html_hash=rendered.html_hash,
        warnings=["Resume exceeds its page target."]
        if rendered.page_count > validated.metadata.target_page_limit
        else [],
    )
