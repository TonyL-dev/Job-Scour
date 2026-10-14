import base64
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ai.gateway import Gateway
from app.ai.generation import Writer, claim_check, source_text
from app.ai.operations import cancel, operation
from app.ai.phase6 import provenance, write_letter
from app.career import service as career
from app.core.workspace import validate_session
from app.cover_letters import repository
from app.cover_letters.schemas import (
    LetterContent,
    LetterEdit,
    LetterRun,
    LetterSave,
    LetterStart,
    LetterVersion,
)
from app.jobs import service as jobs
from app.rendering import service as rendering
from app.resumes import service as resumes
from app.resumes.schemas import Item, Metadata, Preview, ResumeDocument, Section
from app.settings import service as settings


def list_runs(db: Session, owner: UUID) -> list[LetterRun]:
    return repository.list_runs(db, owner)


def list_versions(db: Session, owner: UUID) -> list[LetterVersion]:
    return repository.list_versions(db, owner)


def get_run(db: Session, owner: UUID, identifier: UUID) -> LetterRun:
    return repository.get_run(db, owner, identifier)


def get_version(db: Session, owner: UUID, identifier: UUID) -> LetterVersion:
    return repository.get_version(db, owner, identifier)


def payload(run: LetterRun) -> dict[str, object]:
    return run.model_dump(mode="json", exclude={"id", "revision", "status", "saved_version_id"})


def evidence(db: Session, owner: UUID, data: LetterStart) -> dict[str, str]:
    return {
        str(ref.entity_id): source_text(career.get(db, owner, ref.entity_type, ref.entity_id))
        for ref in data.sources
    }


def start(db: Session, owner: UUID, data: LetterStart) -> LetterRun:
    jobs.get(db, owner, data.job_id)
    analysis = jobs.analysis(db, owner, data.analysis_id)
    if analysis[0] != data.job_id:
        raise HTTPException(422, "Analysis must belong to the selected job")
    if data.resume_version_id:
        resumes.get_version(db, owner, data.resume_version_id)
    if data.content.paragraphs:
        raise HTTPException(422, "Generation starts from contact fields and selected evidence")
    sources = evidence(db, owner, data)
    if len(sources) != len(data.sources):
        raise HTTPException(422, "Select unique career source records")
    return repository.create_run(
        db,
        owner,
        {
            "request": data.model_dump(mode="json"),
            "proposed": data.content.model_dump(mode="json"),
            "support": {},
            "reasons": {},
            "evidence": sources,
            "provenance": {},
            "error": None,
        },
    )


async def execute(
    db: Session, owner: UUID, identifier: UUID, revision: int, gateway: Gateway
) -> LetterRun:
    run = repository.get_run(db, owner, identifier)
    if run.status != "queued" or run.revision != revision:
        raise HTTPException(409, "Run already started or changed; reload")
    endpoint, profile = settings.resolve(db, owner, "cover_letter")
    verifier = Writer(gateway, {"verification": settings.resolve(db, owner, "verification")})
    run = repository.change_run(db, owner, run, payload(run), "running")
    db.commit()
    try:
        async with operation(owner, run.id):
            analysis = jobs.analysis(db, owner, run.request.analysis_id)[1]
            paragraphs = await write_letter(
                gateway, endpoint, profile, run.evidence, analysis, run.request.max_words
            )
            supported: dict[str, str] = {}
            reasons: dict[str, str] = {}
            selected = {r.entity_id: r for r in run.request.sources}
            if sum(len(p.text.split()) for p in paragraphs.paragraphs) > run.request.max_words:
                raise HTTPException(502, "Model exceeded the cover-letter word limit")
            validated = []
            for proposal in paragraphs.paragraphs:
                ids = [r.entity_id for r in proposal.source_refs]
                key = str(proposal.key)
                proposal = proposal.model_copy(
                    update={"origin": "ai", "facts": None, "locked": False}
                )
                reason = claim_check(
                    proposal.text, {UUID(k): v for k, v in run.evidence.items()}, ids, []
                )
                if any(
                    ref.entity_id not in selected or ref != selected[ref.entity_id]
                    for ref in proposal.source_refs
                ):
                    reason = "Source membership does not match selected evidence"
                if reason:
                    supported[key], reasons[key] = "unsupported", reason
                else:
                    verification = await verifier.verify(
                        proposal.text,
                        {UUID(k): v for k, v in run.evidence.items() if UUID(k) in ids},
                    )
                    supported[key], reasons[key] = verification.status, verification.reason
                validated.append(proposal)
            if len({p.key for p in validated}) != len(validated):
                raise HTTPException(502, "Model returned duplicate paragraph keys")
            validate_session(db)
            if evidence(db, owner, run.request) != run.evidence:
                raise HTTPException(409, "Career evidence changed during generation; start again")
            run.proposed = run.request.content.model_copy(update={"paragraphs": validated})
            run.support, run.reasons = supported, reasons
            run.provenance = {
                **verifier.provenance,
                "cover_letter_model": profile.model,
                "cover_letter_provider": endpoint.provider,
                "cover_letter_sampling": "codex-managed"
                if endpoint.provider == "codex"
                else str(profile.temperature),
                **{
                    f"cover_letter_{k}": v
                    for k, v in provenance("cover_letter", endpoint, profile).items()
                },
            }
            result = repository.change_run(db, owner, run, payload(run), "review")
            db.commit()
            return result
    except HTTPException as error:
        validate_session(db)
        run.error = "Cover letter generation failed or cancelled; start a new run"
        result = repository.change_run(
            db,
            owner,
            run,
            payload(run),
            "cancelled" if "cancelled" in str(error.detail) else "failed",
        )
        db.commit()
        return result


def validate_content(
    db: Session,
    owner: UUID,
    content: LetterContent,
    original: LetterContent,
    support: dict[str, str],
    original_evidence: dict[str, str] | None = None,
) -> None:
    if not content.paragraphs or len({p.key for p in content.paragraphs}) != len(
        content.paragraphs
    ):
        raise HTTPException(422, "Keep at least one paragraph with unique keys")
    for item in content.paragraphs:
        records = [
            career.get(db, owner, ref.entity_type, ref.entity_id) for ref in item.source_refs
        ]
        career.guard_records(db, owner, records)
        facts = {record.id: source_text(record) for record in records}
        if not facts:
            raise HTTPException(422, "Career paragraphs need active source references")
        if item.origin == "ai":
            previous = next((p for p in original.paragraphs if p.key == item.key), None)
            if previous != item or support.get(str(item.key)) != "supported":
                raise HTTPException(
                    422,
                    "Only unchanged supported AI paragraphs may be accepted; edit with user origin",
                )
            if original_evidence and any(
                original_evidence.get(str(k)) != v for k, v in facts.items()
            ):
                raise HTTPException(409, "AI source evidence changed; generate again")
            if reason := claim_check(item.text, facts, list(facts), []):
                raise HTTPException(422, reason)


def commit(db: Session, owner: UUID, identifier: UUID, data: LetterSave) -> LetterVersion:
    run = repository.get_run(db, owner, identifier)
    if run.saved_version_id:
        return repository.get_version(db, owner, run.saved_version_id)
    if run.status != "review" or run.revision != data.expected_revision:
        raise HTTPException(409, "Letter review changed; reload")
    validate_content(db, owner, data.content, run.proposed, run.support, run.evidence)
    try:
        repository.change_run(db, owner, run, payload(run), "review")
        version = repository.save_version(
            db,
            owner,
            {
                "title": data.title,
                "job_id": str(run.request.job_id),
                "content": data.content.model_dump(mode="json"),
                "provenance": run.provenance,
            },
        )
        updated = repository.get_run(db, owner, identifier)
        repository.change_run(db, owner, updated, payload(updated), "committed", version.id)
        db.commit()
        return version
    except BaseException:
        db.rollback()
        raise


def edit(db: Session, owner: UUID, identifier: UUID, data: LetterEdit) -> LetterVersion:
    original = repository.get_version(db, owner, identifier)
    support = {str(p.key): "supported" for p in original.content.paragraphs if p.origin == "ai"}
    validate_content(db, owner, data.content, original.content, support)
    try:
        result = repository.save_version(
            db,
            owner,
            {
                "title": original.title,
                "job_id": str(original.job_id),
                "content": data.content.model_dump(mode="json"),
                "provenance": original.provenance,
            },
            original.document_id,
            data.expected_version,
        )
        db.commit()
        return result
    except BaseException:
        db.rollback()
        raise


def restore(db: Session, owner: UUID, identifier: UUID, expected_version: int) -> LetterVersion:
    historical = repository.get_version(db, owner, identifier)
    result = repository.save_version(
        db,
        owner,
        {
            "title": historical.title,
            "job_id": str(historical.job_id),
            "content": historical.content.model_dump(mode="json"),
            "provenance": {**historical.provenance, "restored_from": str(historical.id)},
        },
        historical.document_id,
        expected_version,
    )
    db.commit()
    return result


def cancel_run(db: Session, owner: UUID, identifier: UUID) -> None:
    run = repository.get_run(db, owner, identifier)
    cancel(owner, identifier)
    if run.status == "queued":
        repository.change_run(db, owner, run, payload(run), "cancelled")
        db.commit()


def document(content: LetterContent) -> ResumeDocument:
    paragraphs = [
        Item(key=uuid4(), text=content.salutation, origin="user", source_refs=[]),
        *content.paragraphs,
        Item(
            key=uuid4(),
            text=content.closing + "\n" + content.author.name,
            origin="user",
            source_refs=[],
        ),
    ]
    return ResumeDocument(
        schema_version=1,
        header=content.author,
        sections=[
            Section(
                key=uuid4(),
                type="summary",
                title=content.recipient or "Cover letter",
                items=paragraphs,
            )
        ],
        metadata=Metadata(template_id=rendering.TEMPLATES[0].id),
    )


def render(content: LetterContent) -> rendering.Rendered:
    return resumes.render(document(content))


def export_docx(db: Session, owner: UUID, identifier: UUID) -> bytes:
    from app.rendering.docx import export

    return export(document(repository.get_version(db, owner, identifier).content))


def preview(db: Session, owner: UUID, identifier: UUID) -> Preview:
    artifact = render(repository.get_version(db, owner, identifier).content)
    return Preview(
        html=artifact.html,
        pdf_base64=base64.b64encode(artifact.pdf).decode(),
        page_count=artifact.page_count,
        html_hash=artifact.html_hash,
        warnings=["Cover letter exceeds one page"] if artifact.page_count > 1 else [],
    )
