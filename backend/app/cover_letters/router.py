from uuid import UUID

from fastapi import APIRouter, Request, Response

from app.auth.service import Database, Owner
from app.cover_letters import service
from app.cover_letters.schemas import LetterEdit, LetterRun, LetterSave, LetterStart, LetterVersion
from app.resumes.schemas import Preview

router = APIRouter(prefix="/api/letters", tags=["cover_letters"])


@router.get("/runs")
def runs(db: Database, owner: Owner) -> list[LetterRun]:
    return service.list_runs(db, owner)


@router.post("/runs", status_code=201)
def start(data: LetterStart, db: Database, owner: Owner) -> LetterRun:
    return service.start(db, owner, data)


@router.get("/runs/{identifier}")
def get_run(identifier: UUID, db: Database, owner: Owner) -> LetterRun:
    return service.get_run(db, owner, identifier)


@router.post("/runs/{identifier}/execute")
async def execute(
    identifier: UUID, revision: int, request: Request, db: Database, owner: Owner
) -> LetterRun:
    return await service.execute(db, owner, identifier, revision, request.app.state.gateway)


@router.post("/runs/{identifier}/cancel", status_code=204)
async def cancel(identifier: UUID, db: Database, owner: Owner) -> Response:
    service.cancel_run(db, owner, identifier)
    return Response(status_code=204)


@router.post("/runs/{identifier}/commit")
def commit(identifier: UUID, data: LetterSave, db: Database, owner: Owner) -> LetterVersion:
    return service.commit(db, owner, identifier, data)


@router.get("/versions")
def versions(db: Database, owner: Owner) -> list[LetterVersion]:
    return service.list_versions(db, owner)


@router.get("/versions/{identifier}")
def version(identifier: UUID, db: Database, owner: Owner) -> LetterVersion:
    return service.get_version(db, owner, identifier)


@router.put("/versions/{identifier}")
def edit(identifier: UUID, data: LetterEdit, db: Database, owner: Owner) -> LetterVersion:
    return service.edit(db, owner, identifier, data)


@router.post("/versions/{identifier}/restore")
def restore(identifier: UUID, expected_version: int, db: Database, owner: Owner) -> LetterVersion:
    return service.restore(db, owner, identifier, expected_version)


@router.get("/versions/{identifier}/preview")
def preview(identifier: UUID, db: Database, owner: Owner) -> Preview:
    return service.preview(db, owner, identifier)


@router.get("/versions/{identifier}/pdf")
def pdf(identifier: UUID, db: Database, owner: Owner) -> Response:
    version = service.get_version(db, owner, identifier)
    filename = f"cover-letter-v{version.version_number}.pdf"
    return Response(
        service.render(version.content).pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/versions/{identifier}/docx", response_class=Response)
def docx(identifier: UUID, db: Database, owner: Owner) -> Response:
    from app.rendering.docx import MIME

    return Response(
        service.export_docx(db, owner, identifier),
        media_type=MIME,
        headers={"Content-Disposition": 'attachment; filename="cover-letter-version.docx"'},
    )
