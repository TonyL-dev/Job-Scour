"""Bounded document parsing worker. No application config, network or model calls."""

import io
import json
import sys
import zipfile
from pathlib import PurePosixPath
from xml.etree import ElementTree as ET

from pypdf import PdfReader
from pypdf.generic import DictionaryObject

MAX_UPLOAD = 2 * 1024 * 1024
MAX_TEXT = 200000
MAX_PAGES = 30
MAX_MEMBERS = 256
MAX_EXPANDED = 8 * 1024 * 1024
MAX_FRAGMENTS = 500


def parse(content: bytes, kind: str) -> list[dict[str, str]]:
    if not content or len(content) > MAX_UPLOAD:
        raise ValueError("Upload must contain at most 2 MiB")
    fragments: list[dict[str, str]] = []
    if kind == "pdf":
        if not content.startswith(b"%PDF-"):
            raise ValueError("File signature is not PDF")
        if any(
            marker in content for marker in (b"/JavaScript", b"/JS", b"/Launch", b"/EmbeddedFile")
        ):
            raise ValueError("Active or embedded PDF content is unsupported")
        reader = PdfReader(io.BytesIO(content), strict=True)
        if reader.is_encrypted:
            raise ValueError("Password-protected PDF is unsupported")
        if len(reader.pages) > MAX_PAGES:
            raise ValueError("PDF exceeds 30 pages")
        pdf_root = reader.trailer["/Root"]
        if not isinstance(pdf_root, DictionaryObject):
            raise ValueError("Invalid PDF catalog")
        if any(key in pdf_root for key in ("/OpenAction", "/AA")):
            raise ValueError("PDF document actions are unsupported")
        names = pdf_root.get("/Names")
        if names:
            dictionary = names.get_object()
            if not isinstance(dictionary, DictionaryObject) or any(
                key in dictionary for key in ("/JavaScript", "/EmbeddedFiles")
            ):
                raise ValueError("PDF scripts and attachments are unsupported")
        for number, page in enumerate(reader.pages, 1):
            if "/AA" in page:
                raise ValueError("PDF page actions are unsupported")
            for reference in page.get("/Annots", []):
                annotation = reference.get_object()
                action = annotation.get("/A")
                if "/AA" in annotation or (
                    action
                    and action.get_object().get("/S")
                    in {"/JavaScript", "/Launch", "/SubmitForm", "/ImportData", "/GoToR"}
                ):
                    raise ValueError("Active PDF annotations are unsupported")
            fragments.append({"locator": f"page {number}", "text": page.extract_text() or ""})
    elif kind == "docx":
        if not content.startswith(b"PK\x03\x04"):
            raise ValueError("File signature is not DOCX")
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = archive.infolist()
            if len(members) > MAX_MEMBERS or sum(m.file_size for m in members) > MAX_EXPANDED:
                raise ValueError("DOCX exceeds 256 entries or 8 MiB expanded size")
            if len({m.filename for m in members}) != len(members):
                raise ValueError("Duplicate archive entries")
            for member in members:
                name = member.filename
                if (
                    "\\" in name
                    or PurePosixPath(name).is_absolute()
                    or ".." in PurePosixPath(name).parts
                ):
                    raise ValueError("Unsafe archive path")
                if any(part in name.lower() for part in ("vbaproject", "embeddings/", "activex/")):
                    raise ValueError("Active or embedded DOCX content is unsupported")
                if name.endswith((".xml", ".rels")):
                    raw = archive.read(member)
                    normalized = raw.replace(b"\x00", b"").upper()
                    if b"<!DOCTYPE" in normalized or b"<!ENTITY" in normalized:
                        raise ValueError("XML entities are unsupported")
                    root = ET.fromstring(raw)
                    if name.endswith(".rels"):
                        for rel in root:
                            if rel.attrib.get("TargetMode") == "External" and not rel.attrib.get(
                                "Type", ""
                            ).endswith("/hyperlink"):
                                raise ValueError("External document relationships are unsupported")
            document = ET.fromstring(archive.read("word/document.xml"))
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            for number, paragraph in enumerate(document.findall(".//w:p", ns), 1):
                text = "".join(t.text or "" for t in paragraph.findall(".//w:t", ns))
                if text.strip():
                    fragments.append({"locator": f"paragraph {number}", "text": text})
    else:
        raise ValueError("Unsupported document format")
    if sum(len(f["text"]) for f in fragments) > MAX_TEXT:
        raise ValueError("Extracted text exceeds 200000 characters")
    if len(fragments) > MAX_FRAGMENTS:
        raise ValueError("Document exceeds 500 text fragments")
    if not any(f["text"].strip() for f in fragments):
        raise ValueError("No extractable text. Image-only PDF/OCR is unsupported")
    return fragments


if __name__ == "__main__":
    try:
        result = parse(sys.stdin.buffer.read(MAX_UPLOAD + 1), sys.argv[1])
        sys.stdout.write(json.dumps({"fragments": result}))
    except Exception:
        # Parser exception details can contain document text; never expose them.
        sys.stdout.write(
            json.dumps(
                {
                    "error": "Unsupported, corrupt, encrypted or oversized document. "
                    "Text PDF/DOCX only; OCR is unsupported."
                }
            )
        )
        sys.exit(1)
