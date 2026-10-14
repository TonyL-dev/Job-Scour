import base64
import hashlib
import io
import json
import re
import struct
import zlib
from uuid import UUID, uuid4

from fastapi import HTTPException
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.core import private_files
from app.rendering import service as rendering
from app.resumes.schemas import (
    Header,
    Item,
    Metadata,
    Preview,
    ResumeDocument,
    Section,
    TemplateInfo,
)
from app.templates import repository, validation
from app.templates.schemas import Asset, AssetUpload, CustomTemplate, TemplateSave, TemplateSnapshot


def list_templates(db: Session, owner: UUID) -> list[CustomTemplate]:
    return repository.list_templates(db, owner)


def list_assets(db: Session, owner: UUID) -> list[Asset]:
    return repository.list_assets(db, owner)


def snapshot(db: Session, owner: UUID, identifier: UUID, active: bool = True) -> TemplateSnapshot:
    template = repository.get(db, owner, identifier)
    if active and template.retired:
        raise HTTPException(422, "Choose an active template revision")
    return template.snapshot


def template_infos(db: Session, owner: UUID) -> list[TemplateInfo]:
    return [
        TemplateInfo(
            id=t.id,
            name=f"{t.snapshot.name} · revision {t.revision}",
            builtin_key=t.snapshot.base,
            ats_safe=False,
            default_styles=t.snapshot.styles,
        )
        for t in repository.list_templates(db, owner)
        if not t.retired
    ]


def prepare(db: Session, owner: UUID, data: TemplateSave) -> TemplateSnapshot:
    validation.validate(data.html, data.css, set(data.asset_ids))
    if data.styles.accent_color and validation.contrast(data.styles.accent_color, "#ffffff") < 4.5:
        raise HTTPException(422, "Template accent contrast must be at least 4.5:1 on white")
    assets = {}
    for identifier in data.asset_ids:
        _, ciphertext = repository.asset(db, owner, identifier)
        private_files.decrypt(ciphertext, owner, identifier)
        assets[str(identifier)] = ciphertext
    digest = hashlib.sha256(
        json.dumps(
            data.model_dump(mode="json", exclude={"expected_revision"}), sort_keys=True
        ).encode()
    ).hexdigest()
    return TemplateSnapshot(
        owner_id=owner,
        name=data.name,
        base=data.base,
        html=data.html,
        css=data.css,
        styles=data.styles,
        assets=assets,
        digest=digest,
    )


def save(
    db: Session, owner: UUID, data: TemplateSave, document_id: UUID | None = None
) -> CustomTemplate:
    custom = prepare(db, owner, data)
    measured = preview_example(db, owner, data)
    custom.findings = measured.warnings
    return repository.save(db, owner, custom, document_id, data.expected_revision)


def retire(db: Session, owner: UUID, identifier: UUID) -> None:
    repository.retire(db, owner, identifier)


def preview(
    db: Session, owner: UUID, data: TemplateSave, content: ResumeDocument
) -> rendering.Rendered:
    # Preview uses synthetic text only, never bypasses career-source validation for a draft.
    custom = prepare(db, owner, data)
    example = content.model_copy(deep=True)
    example.metadata = Metadata(template_id=uuid4(), custom_template=custom)
    return rendering.render(example)


def preview_example(db: Session, owner: UUID, data: TemplateSave) -> Preview:
    content = ResumeDocument(
        schema_version=1,
        header=Header(name="Synthetic Candidate", email="candidate@example.invalid"),
        sections=[
            Section(
                key=uuid4(),
                type="experience",
                title="Experience",
                items=[
                    Item(
                        key=uuid4(),
                        text="Built Python APIs and reduced latency by 40%.",
                        origin="user",
                        source_refs=[],
                    )
                ],
            )
        ],
        metadata=Metadata(template_id=rendering.TEMPLATES[0].id),
    )
    result = preview(db, owner, data, content)
    return Preview(
        html=result.html,
        pdf_base64=base64.b64encode(result.pdf).decode(),
        page_count=result.page_count,
        html_hash=result.html_hash,
        warnings=validation.validate(data.html, data.css, set(data.asset_ids))
        + inspect_layout(result),
    )


def inspect_layout(result: rendering.Rendered) -> list[str]:
    text = re.sub(
        r"\s+",
        " ",
        " ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(result.pdf)).pages),
    )
    expected = [
        "Synthetic Candidate",
        "candidate@example.invalid",
        "Experience",
        "Built Python APIs and reduced latency by 40%.",
    ]
    positions = [text.find(value) for value in expected]
    findings = []
    if any(position < 0 for position in positions):
        findings.append(
            "Synthetic PDF extraction omitted or fragmented expected headings/contact/content; "
            "review this layout before use."
        )
    elif positions != sorted(positions):
        findings.append(
            "Synthetic PDF reading order differs from canonical header/section order; "
            "review ATS findings before use."
        )
    if result.page_count > 2:
        findings.append(f"Synthetic template content overflows to {result.page_count} pages.")
    return findings


def upload_asset(db: Session, owner: UUID, data: AssetUpload) -> Asset:
    if len(repository.list_assets(db, owner)) >= 100:
        raise HTTPException(429, "Local asset limit is 100")
    try:
        raw = base64.b64decode(data.content_base64, validate=True)
        if not raw.startswith(b"\x89PNG\r\n\x1a\n") or len(raw) > 256 * 1024:
            raise ValueError("Use a PNG up to 256 KiB")
        offset, compressed = 8, b""
        chunks: list[bytes] = []
        width = height = channels = 0
        ended = False
        while offset < len(raw):
            length = struct.unpack(">I", raw[offset : offset + 4])[0]
            kind = raw[offset + 4 : offset + 8]
            data_bytes = raw[offset + 8 : offset + 8 + length]
            crc = raw[offset + 8 + length : offset + 12 + length]
            if len(crc) != 4 or zlib.crc32(kind + data_bytes) != struct.unpack(">I", crc)[0]:
                raise ValueError("Invalid PNG checksum")
            chunk = raw[offset : offset + length + 12]
            if kind == b"IHDR":
                if chunks or length != 13:
                    raise ValueError("Invalid PNG header")
                width, height, depth, color, compression, filtering, interlace = struct.unpack(
                    ">IIBBBBB", data_bytes
                )
                if (
                    not (1 <= width <= 1024 and 1 <= height <= 1024)
                    or depth != 8
                    or color not in {2, 6}
                    or compression
                    or filtering
                    or interlace
                ):
                    raise ValueError("Use a non-interlaced RGB/RGBA PNG up to 1024 pixels per side")
                channels = 3 if color == 2 else 4
                chunks.append(chunk)
            elif kind == b"IDAT":
                compressed += data_bytes
                chunks.append(chunk)
            elif kind == b"IEND":
                if length or offset + 12 != len(raw):
                    raise ValueError("Invalid PNG end")
                chunks.append(chunk)
                ended = True
            elif kind in {b"acTL", b"fcTL", b"fdAT"}:
                raise ValueError("Animated PNG is unsupported")
            elif kind[:1].isupper():
                raise ValueError("Unsupported PNG encoding")
            offset += length + 12
        expected = height * (width * channels + 1)
        decoder = zlib.decompressobj()
        pixels = decoder.decompress(compressed, expected + 1)
        if (
            not ended
            or not channels
            or len(pixels) != expected
            or not decoder.eof
            or decoder.unused_data
            or decoder.unconsumed_tail
            or any(pixels[n] > 4 for n in range(0, expected, width * channels + 1))
        ):
            raise ValueError("Invalid or oversized PNG pixel data")
        sanitized = b"\x89PNG\r\n\x1a\n" + b"".join(chunks)
    except (ValueError, struct.error, zlib.error) as error:
        raise HTTPException(422, "Unsupported local asset: " + str(error)) from error
    identifier = uuid4()
    return repository.save_asset(
        db, owner, identifier, private_files.encrypt(sanitized, owner, identifier), width, height
    )
