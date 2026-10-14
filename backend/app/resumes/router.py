from uuid import UUID

from fastapi import APIRouter, Response

from app.auth.service import Database, Owner
from app.resumes import schemas, service
from app.resumes.schemas import MasterResume, Preview, ResumeDocument, SaveResume, TemplateInfo

router = APIRouter(prefix="/api/resumes", tags=["resumes"])


@router.get("/templates")
def templates(session: Database, owner: Owner) -> list[TemplateInfo]:
    return service.templates(session, owner)


@router.get("")
def list_resumes(session: Database, owner: Owner) -> list[MasterResume]:
    return service.list_resumes(session, owner)


@router.post("", status_code=201)
def create(data: SaveResume, session: Database, owner: Owner) -> MasterResume:
    return service.save(session, owner, data)


@router.post("/preview")
def preview(content: ResumeDocument, session: Database, owner: Owner) -> Preview:
    return service.preview(session, owner, content)


@router.get("/{identifier}")
def get(identifier: UUID, session: Database, owner: Owner) -> MasterResume:
    return service.get(session, owner, identifier)


@router.put("/{identifier}")
def save(identifier: UUID, data: SaveResume, session: Database, owner: Owner) -> MasterResume:
    return service.save(session, owner, data, identifier)


@router.get(
    "/{identifier}/pdf",
    response_class=Response,
    responses={
        200: {"content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}}}
    },
)
def pdf(identifier: UUID, session: Database, owner: Owner) -> Response:
    content = service.get(session, owner, identifier).content
    result = service.render(content)
    return Response(
        content=result.pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="resume.pdf"',
            "X-Page-Count": str(result.page_count),
            "X-HTML-Hash": result.html_hash,
            "Cache-Control": "no-store",
        },
    )


@router.get("/{identifier}/versions")
def history(identifier: UUID, session: Database, owner: Owner) -> list[schemas.ResumeVersion]:
    return service.history(session, owner, identifier)


@router.get("/versions/{identifier}")
def version(identifier: UUID, session: Database, owner: Owner) -> schemas.ResumeVersion:
    return service.get_version(session, owner, identifier)


@router.post("/versions/{identifier}/restore")
def restore(
    identifier: UUID, data: schemas.VersionAction, session: Database, owner: Owner
) -> MasterResume:
    return service.version_action(session, owner, identifier, data, False)


@router.post("/versions/{identifier}/duplicate", status_code=201)
def duplicate(
    identifier: UUID, data: schemas.VersionAction, session: Database, owner: Owner
) -> MasterResume:
    return service.version_action(session, owner, identifier, data, True)


@router.get("/versions/{identifier}/pdf", response_class=Response)
def version_pdf(identifier: UUID, session: Database, owner: Owner) -> Response:
    result = service.render(service.get_version(session, owner, identifier).content)
    return Response(result.pdf, media_type="application/pdf", headers={"Cache-Control": "no-store"})


@router.get("/versions/{identifier}/docx", response_class=Response)
def version_docx(identifier: UUID, session: Database, owner: Owner) -> Response:
    from app.rendering.docx import MIME

    return Response(
        service.export_docx(session, owner, identifier),
        media_type=MIME,
        headers={"Content-Disposition": 'attachment; filename="resume-version.docx"'},
    )


@router.post("/{identifier}/preview")
def manual_preview(
    identifier: UUID, content: ResumeDocument, session: Database, owner: Owner
) -> Preview:
    return service.manual_preview(session, owner, identifier, content)
