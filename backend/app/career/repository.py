from uuid import UUID

from fastapi import HTTPException
from pydantic import TypeAdapter
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.career.models import MODELS, CareerBase
from app.career.schemas import CareerInput, CareerRecord
from app.core.database import utc_now

adapter: TypeAdapter[CareerInput] = TypeAdapter(CareerInput)


def serialize(row: CareerBase, kind: str) -> CareerRecord:
    values = {column.name: getattr(row, column.name) for column in row.__table__.columns}
    return CareerRecord(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
        data=adapter.validate_python(
            {
                "type": kind,
                **{key: value for key, value in values.items() if key in adapter_fields(kind)},
            }
        ),
    )


def adapter_fields(kind: str) -> set[str]:
    return set(MODELS[kind].__table__.columns.keys()) - {
        "id",
        "user_id",
        "created_at",
        "updated_at",
        "deleted_at",
        "normalized_name",
    }


def list_records(session: Session, owner: UUID, kind: str) -> list[CareerRecord]:
    model = MODELS[kind]
    rows = session.scalars(
        select(model)
        .where(model.user_id == owner, model.deleted_at.is_(None))
        .order_by(model.created_at, model.id)
    )
    return [serialize(row, kind) for row in rows]


def find(session: Session, owner: UUID, kind: str, identifier: UUID) -> CareerBase | None:
    model = MODELS[kind]
    return session.scalar(
        select(model).where(
            model.user_id == owner, model.id == identifier, model.deleted_at.is_(None)
        )
    )


def save(
    session: Session,
    owner: UUID,
    data: CareerInput,
    row: CareerBase | None = None,
    *,
    commit: bool = True,
) -> CareerRecord:
    kind = data.type
    values = data.model_dump(mode="python", exclude={"type"})
    for key, value in values.items():
        if key == "url" and value is not None:
            values[key] = str(value)
    if kind == "skill":
        values["normalized_name"] = str(values["name"]).casefold()
    row = row or MODELS[kind](user_id=owner)
    for key, value in values.items():
        setattr(row, key, value)
    session.add(row)
    if commit:
        session.commit()
    else:
        session.flush()
    session.refresh(row)
    return serialize(row, kind)


def retire(session: Session, row: CareerBase) -> None:
    row.deleted_at = utc_now()
    session.commit()


def reserve_revision(session: Session, owner: UUID, record: CareerRecord) -> None:
    model = MODELS[record.data.type]
    result = session.execute(
        update(model)
        .where(
            model.user_id == owner,
            model.id == record.id,
            model.updated_at == record.updated_at,
            model.deleted_at.is_(None),
        )
        .values(updated_at=utc_now())
    )
    if result.rowcount != 1:  # type: ignore[attr-defined]
        raise HTTPException(409, "Career record changed; refresh review")


def guard_active(session: Session, owner: UUID, record: CareerRecord) -> None:
    # A conditional no-op write holds the source row through the surrounding transaction,
    # without changing recency/provenance timestamps. SQLite also reserves the writer slot.
    model = MODELS[record.data.type]
    result = session.execute(
        update(model)
        .where(
            model.user_id == owner,
            model.id == record.id,
            model.updated_at == record.updated_at,
            model.deleted_at.is_(None),
        )
        .values(updated_at=record.updated_at)
    )
    if result.rowcount != 1:  # type: ignore[attr-defined]
        raise HTTPException(409, "Career source changed; refresh before accepting")
