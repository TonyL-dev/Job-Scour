from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.templates.models import TemplateAsset, TemplateDocument, TemplateRevision
from app.templates.schemas import Asset, CustomTemplate, TemplateSnapshot


def get(db: Session, owner: UUID, identifier: UUID) -> CustomTemplate:
    row = db.scalar(
        select(TemplateRevision).where(
            TemplateRevision.user_id == owner, TemplateRevision.id == identifier
        )
    )
    if row is None:
        raise HTTPException(404, "Template revision not found")
    doc = db.scalar(
        select(TemplateDocument).where(
            TemplateDocument.user_id == owner, TemplateDocument.id == row.document_id
        )
    )
    assert doc is not None
    return CustomTemplate(
        id=row.id,
        document_id=row.document_id,
        revision=row.revision,
        retired=doc.retired,
        snapshot=TemplateSnapshot.model_validate(row.payload),
    )


def list_templates(db: Session, owner: UUID) -> list[CustomTemplate]:
    return [
        get(db, owner, row.id)
        for row in db.scalars(
            select(TemplateRevision)
            .where(TemplateRevision.user_id == owner)
            .order_by(TemplateRevision.created_at.desc())
            .limit(200)
        )
    ]


def save(
    db: Session, owner: UUID, snapshot: TemplateSnapshot, document_id: UUID | None, expected: int
) -> CustomTemplate:
    if document_id:
        result = db.execute(
            update(TemplateDocument)
            .where(
                TemplateDocument.user_id == owner,
                TemplateDocument.id == document_id,
                TemplateDocument.latest_revision == expected,
                TemplateDocument.retired.is_(False),
            )
            .values(latest_revision=expected + 1, name=snapshot.name)
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise HTTPException(409, "Template changed or retired; reload")
        revision = expected + 1
    else:
        if expected != 0:
            raise HTTPException(409, "New templates require revision zero")
        doc = TemplateDocument(user_id=owner, name=snapshot.name)
        db.add(doc)
        db.flush()
        document_id, revision = doc.id, 1
    row = TemplateRevision(
        user_id=owner,
        document_id=document_id,
        revision=revision,
        payload=snapshot.model_dump(mode="json"),
    )
    db.add(row)
    db.commit()
    return get(db, owner, row.id)


def retire(db: Session, owner: UUID, identifier: UUID) -> None:
    get(db, owner, identifier)
    document_id = get(db, owner, identifier).document_id
    db.execute(
        update(TemplateDocument)
        .where(TemplateDocument.user_id == owner, TemplateDocument.id == document_id)
        .values(retired=True)
    )
    db.commit()


def asset(db: Session, owner: UUID, identifier: UUID) -> tuple[Asset, str]:
    row = db.scalar(
        select(TemplateAsset).where(TemplateAsset.user_id == owner, TemplateAsset.id == identifier)
    )
    if row is None:
        raise HTTPException(404, "Template asset not found")
    return Asset(id=row.id, width=row.width, height=row.height), row.ciphertext


def save_asset(
    db: Session, owner: UUID, identifier: UUID, ciphertext: str, width: int, height: int
) -> Asset:
    db.add(
        TemplateAsset(
            id=identifier, user_id=owner, ciphertext=ciphertext, width=width, height=height
        )
    )
    db.commit()
    return Asset(id=identifier, width=width, height=height)


def list_assets(db: Session, owner: UUID) -> list[Asset]:
    return [
        Asset(id=r.id, width=r.width, height=r.height)
        for r in db.scalars(select(TemplateAsset).where(TemplateAsset.user_id == owner).limit(100))
    ]
