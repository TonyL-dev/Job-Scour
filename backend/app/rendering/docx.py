"""Editable OOXML exports from content snapshots; no model or database access."""

import io
import zipfile
from html import escape
from pathlib import Path
from threading import BoundedSemaphore
from uuid import UUID

from fastapi import HTTPException

from app.resumes.schemas import ResumeDocument

LIMIT = BoundedSemaphore(2)
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def paragraph(text: str, style: str = "Normal", bullet: bool = False) -> str:
    if any(ord(char) < 32 and char not in "\t\n\r" for char in text):
        raise HTTPException(422, "DOCX cannot encode control characters; correct this text first")
    numbering = '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>' if bullet else ""
    lines = text.splitlines() or [""]
    runs = "<w:br/>".join(f'<w:t xml:space="preserve">{escape(line)}</w:t>' for line in lines)
    return f'<w:p><w:pPr><w:pStyle w:val="{style}"/>{numbering}</w:pPr><w:r>{runs}</w:r></w:p>'


def export(document: ResumeDocument) -> bytes:
    custom = document.metadata.custom_template
    if custom and (custom.html != "{{header}}{{sections}}" or custom.css or custom.assets):
        raise HTTPException(
            422,
            "Custom HTML/CSS/assets cannot preserve DOCX layout. "
            "Choose a style-only template with canonical placeholders for DOCX export.",
        )
    if not LIMIT.acquire(blocking=False):
        raise HTTPException(429, "DOCX export busy; retry shortly")
    try:
        return build(document)
    finally:
        LIMIT.release()


def build(document: ResumeDocument) -> bytes:
    parts = [paragraph(document.header.name, "Title")]
    contacts = [
        v for v in (document.header.email, document.header.phone, document.header.location) if v
    ]
    if contacts:
        parts.append(paragraph(" · ".join(contacts)))
    relationships = [
        f'<Relationship Id="styles" Type="{R}/styles" Target="styles.xml"/>',
        f'<Relationship Id="numbering" Type="{R}/numbering" Target="numbering.xml"/>',
        f'<Relationship Id="fonts" Type="{R}/fontTable" Target="fontTable.xml"/>',
    ]
    for index, link in enumerate(document.header.links):
        identifier = f"link{index}"
        relationships.append(
            f'<Relationship Id="{identifier}" Type="{R}/hyperlink" '
            f'Target="{escape(str(link.url), quote=True)}" TargetMode="External"/>'
        )
        parts.append(f"""<w:p>
<w:hyperlink r:id="{identifier}">
<w:r>
<w:t>{escape(link.label)}: {escape(str(link.url))}</w:t>
</w:r>
</w:hyperlink>
</w:p>""")
    for section in document.sections:
        if not section.visible:
            continue
        parts.append(paragraph(section.title, "Heading1"))
        previous = None
        for item in section.items:
            if item.facts and item.facts != previous:
                facts = item.facts
                values = [
                    facts.title,
                    facts.employer,
                    facts.institution,
                    facts.degree,
                    facts.location,
                ]
                if facts.start_date:
                    values.append(
                        str(facts.start_date)
                        + " – "
                        + ("Present" if facts.current else str(facts.end_date or ""))
                    )
                parts.append(paragraph(" · ".join(v for v in values if v), "Heading2"))
            previous = item.facts
            parts.append(
                paragraph(
                    item.text,
                    bullet=section.type in {"experience", "projects"}
                    and not item.experience_summary,
                )
            )
    from app.rendering.service import template_for

    style = template_for(document).default_styles.model_copy(
        update=document.metadata.style_overrides.model_dump(exclude_none=True)
    )
    family = (
        "Noto Serif"
        if style.font_family == "serif"
        or (style.font_family is None and str(document.metadata.template_id).endswith("101"))
        else "Noto Sans"
    )
    font_file = "notoserif.ttf" if family == "Noto Serif" else "notosans.ttf"
    halfpoints = round((style.font_size_pt or 11) * 2)
    margin = round((style.margin_mm or 18) * 1440 / 25.4)
    line = round((style.line_height or 1.3) * 240)
    body = (
        "".join(parts)
        + f"""<w:sectPr>
<w:pgSz w:w="11906" w:h="16838"/>
<w:pgMar w:top="{margin}" w:right="{margin}" w:bottom="{margin}" w:left="{margin}"/>
</w:sectPr>"""
    )
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{W}" xmlns:r="{R}">
<w:body>{body}</w:body>
</w:document>"""
    styles = f"""<w:styles xmlns:w="{W}">
<w:docDefaults>
<w:rPrDefault>
<w:rPr>
<w:rFonts w:ascii="{family}" w:hAnsi="{family}"/>
<w:sz w:val="{halfpoints}"/>
</w:rPr>
</w:rPrDefault>
<w:pPrDefault>
<w:pPr>
<w:spacing w:after="90" w:line="{line}" w:lineRule="auto"/>
<w:widowControl/>
</w:pPr>
</w:pPrDefault>
</w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal">
<w:name w:val="Normal"/>
</w:style>
<w:style w:type="paragraph" w:styleId="Title">
<w:name w:val="Title"/>
<w:basedOn w:val="Normal"/>
<w:pPr>
<w:keepNext/>
<w:spacing w:after="120"/>
</w:pPr>
<w:rPr>
<w:b/>
<w:sz w:val="36"/>
<w:color w:val="000000"/>
</w:rPr>
</w:style>
<w:style w:type="paragraph" w:styleId="Heading1">
<w:name w:val="Heading 1"/>
<w:basedOn w:val="Normal"/>
<w:pPr>
<w:keepNext/>
<w:outlineLvl w:val="0"/>
<w:spacing w:before="160" w:after="90"/>
</w:pPr>
<w:rPr>
<w:b/>
</w:rPr>
</w:style>
<w:style w:type="paragraph" w:styleId="Heading2">
<w:name w:val="Heading 2"/>
<w:basedOn w:val="Normal"/>
<w:pPr>
<w:keepNext/>
<w:outlineLvl w:val="1"/>
</w:pPr>
<w:rPr>
<w:b/>
</w:rPr>
</w:style>
</w:styles>"""
    numbering = f"""<w:numbering xmlns:w="{W}">
<w:abstractNum w:abstractNumId="0">
<w:multiLevelType w:val="singleLevel"/>
<w:lvl w:ilvl="0">
<w:start w:val="1"/>
<w:numFmt w:val="bullet"/>
<w:lvlText w:val="•"/>
<w:lvlJc w:val="left"/>
<w:pPr>
<w:ind w:left="260" w:hanging="200"/>
</w:pPr>
</w:lvl>
</w:abstractNum>
<w:num w:numId="1">
<w:abstractNumId w:val="0"/>
</w:num>
</w:numbering>"""
    # Office font embedding uses the GUID bytes in reverse order to obfuscate 32 bytes.
    font_key = UUID("6f2e9a82-7404-4b74-9bf8-6986e8b25a11")
    font = bytearray((Path(__file__).parent / "fonts" / font_file).read_bytes())
    mask = font_key.bytes[::-1]
    for index in range(32):
        font[index] ^= mask[index % 16]
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr(
            "[Content_Types].xml",
            """<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="odttf"
 ContentType="application/vnd.openxmlformats-officedocument.obfuscatedFont"/>
<Override PartName="/word/document.xml"
 ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml"
 ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/numbering.xml"
 ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
<Override PartName="/word/fontTable.xml"
 ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml"/>
</Types>""",
        )
        bundle.writestr(
            "_rels/.rels",
            f"""<Relationships xmlns="{REL}">
<Relationship Id="document" Type="{R}/officeDocument" Target="word/document.xml"/>
</Relationships>""",
        )
        bundle.writestr("word/document.xml", content)
        bundle.writestr("word/styles.xml", styles)
        bundle.writestr("word/numbering.xml", numbering)
        bundle.writestr(
            "word/_rels/document.xml.rels",
            f'<Relationships xmlns="{REL}">{"".join(relationships)}</Relationships>',
        )
        bundle.writestr(
            "word/fontTable.xml",
            f"""<w:fonts xmlns:w="{W}" xmlns:r="{R}">
<w:font w:name="{family}">
<w:embedRegular r:id="font" w:fontKey="{{{str(font_key).upper()}}}"/>
</w:font>
</w:fonts>""",
        )
        bundle.writestr(
            "word/_rels/fontTable.xml.rels",
            f"""<Relationships xmlns="{REL}">
<Relationship Id="font" Type="{R}/font" Target="fonts/resume.odttf"/>
</Relationships>""",
        )
        bundle.writestr("word/fonts/resume.odttf", font)
    return output.getvalue()
