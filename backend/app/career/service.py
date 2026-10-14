from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.career import repository
from app.career.schemas import (
    INPUT_MODELS,
    CareerForm,
    CareerInput,
    CareerRecord,
    CareerType,
    FormField,
)


def forms() -> list[CareerForm]:
    result = []
    for model in INPUT_MODELS:
        schema = model.model_json_schema()
        fields = []
        for name, raw in schema["properties"].items():
            if name == "type":
                continue
            spec = next((item for item in raw.get("anyOf", []) if item.get("type") != "null"), raw)
            kind = "text"
            if name in RELATIONS or "enum" in spec:
                kind = "select"
            elif spec.get("format") == "date":
                kind = "date"
            elif spec.get("type") == "boolean":
                kind = "checkbox"
            elif name in {"gpa", "years_of_use", "metric_value", "importance", "ordering_hint"}:
                kind = "number"
            elif spec.get("type") == "array":
                kind = "list"
            elif name == "payload":
                kind = "details"
            elif name in {
                "description",
                "text",
                "challenges_solved",
                "results",
                "honors",
                "metric_description",
            }:
                kind = "multiline"
            fields.append(
                FormField(
                    name=name,
                    label={
                        "payload": "Details",
                        "ordering_hint": "Display order",
                        "credential_id": "Credential ID",
                        "url": "URL",
                    }.get(name, name.replace("_id", "").replace("_", " ").capitalize()),
                    input_type=kind,
                    required=name in schema.get("required", []),
                    options=spec.get("enum", []),
                    related_type=RELATIONS.get(name),
                    default_value=raw.get("default"),
                )
            )
        result.append(CareerForm(type=model.model_fields["type"].default, fields=fields))
    return result


RELATIONS = {
    "experience_id": "experience",
    "project_id": "project",
    "education_id": "education",
    "skill_id": "skill",
    "achievement_id": "achievement",
}


def get(session: Session, owner: UUID, kind: CareerType, identifier: UUID) -> CareerRecord:
    row = repository.find(session, owner, kind, identifier)
    if row is None:
        raise HTTPException(404, "Career record not found")
    record = repository.serialize(row, kind)
    for key, target in RELATIONS.items():
        if (parent := getattr(record.data, key, None)) is not None:
            get(session, owner, target, parent)  # type: ignore[arg-type]
    return record


def save(
    session: Session,
    owner: UUID,
    data: CareerInput,
    identifier: UUID | None = None,
    *,
    commit: bool = True,
) -> CareerRecord:
    for key, kind in RELATIONS.items():
        value = getattr(data, key, None)
        if value is not None:
            parent = get(session, owner, kind, value)  # type: ignore[arg-type]
            if not commit:
                guard_records(session, owner, [parent])
    row = None
    if identifier:
        get(session, owner, data.type, identifier)
        row = repository.find(session, owner, data.type, identifier)
    try:
        return repository.save(session, owner, data, row, commit=commit)
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(409, "Duplicate record or invalid relationship") from error


def retire(session: Session, owner: UUID, kind: CareerType, identifier: UUID) -> None:
    get(session, owner, kind, identifier)
    row = repository.find(session, owner, kind, identifier)
    assert row is not None
    repository.retire(session, row)


def list_records(session: Session, owner: UUID, kind: CareerType) -> list[CareerRecord]:
    result = []
    for record in repository.list_records(session, owner, kind):
        try:
            result.append(get(session, owner, kind, record.id))
        except HTTPException as error:
            if error.status_code != 404:
                raise
    return result


def save_if_current(
    session: Session, owner: UUID, record: CareerRecord, data: CareerInput
) -> CareerRecord:
    get(session, owner, record.data.type, record.id)
    repository.reserve_revision(session, owner, record)
    return save(session, owner, data, record.id, commit=False)


def guard_records(session: Session, owner: UUID, records: list[CareerRecord]) -> None:
    sources: dict[tuple[str, UUID], CareerRecord] = {}
    pending = list(records)
    while pending:
        record = pending.pop()
        key = (record.data.type, record.id)
        if key in sources:
            continue
        sources[key] = record
        for field, kind in RELATIONS.items():
            parent = getattr(record.data, field, None)
            if parent is not None:
                pending.append(get(session, owner, kind, parent))  # type: ignore[arg-type]
    for source_key in sorted(sources, key=lambda k: (k[0], str(k[1]))):
        repository.guard_active(session, owner, sources[source_key])
