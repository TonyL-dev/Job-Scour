import base64
import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from html import escape
from io import BytesIO
from pathlib import Path
from threading import BoundedSemaphore, Lock
from uuid import UUID

from playwright.sync_api import Error, sync_playwright
from pypdf import PdfReader

from app.core.private_files import decrypt as decrypt_asset
from app.resumes.schemas import ResumeDocument, StyleOverrides, TemplateInfo
from app.templates.validation import validate as validate_template

TEMPLATES = [
    TemplateInfo(
        id=UUID("00000000-0000-4000-8000-000000000101"),
        name="Classic",
        builtin_key="classic",
        default_styles=StyleOverrides(
            font_family="serif",
            font_size_pt=11,
            line_height=1.3,
            margin_mm=18,
            accent_color="#24362e",
            section_spacing_mm=5,
        ),
    ),
    TemplateInfo(
        id=UUID("00000000-0000-4000-8000-000000000102"),
        name="Modern",
        builtin_key="modern",
        default_styles=StyleOverrides(
            font_family="sans",
            font_size_pt=10.5,
            line_height=1.35,
            margin_mm=18,
            accent_color="#244d3d",
            section_spacing_mm=5,
        ),
    ),
]
RENDER_LIMIT = BoundedSemaphore(2)
CACHE_LOCK = Lock()
CACHE: OrderedDict[str, tuple[float, "Rendered"]] = OrderedDict()
CACHE_BYTES = 24 * 1024 * 1024
CACHE_TTL = 60
cache_epoch = 0


class RendererBusy(Error):
    pass


@lru_cache(maxsize=2)
def font_css(family: str) -> str:
    filename = "notoserif.ttf" if family == "serif" else "notosans.ttf"
    encoded = base64.b64encode((Path(__file__).parent / "fonts" / filename).read_bytes()).decode(
        "ascii"
    )
    return (
        "@font-face { font-family: ResumeFont; font-style: normal; font-weight: 100 900; "
        f"src: url(data:font/ttf;base64,{encoded}) format('truetype'); }}"
    )


@dataclass(frozen=True)
class Rendered:
    html: str
    pdf: bytes
    page_count: int
    html_hash: str


def clear_cache() -> None:
    """Invalidate late renders as well as cached private content."""
    global cache_epoch
    with CACHE_LOCK:
        cache_epoch += 1
        CACHE.clear()


def cached(digest: str) -> Rendered | None:
    with CACHE_LOCK:
        now = time.monotonic()
        for key in list(CACHE):
            if CACHE[key][0] <= now:
                del CACHE[key]
        entry = CACHE.get(digest)
        if entry:
            CACHE.move_to_end(digest)
            return entry[1]
        return None


def retain(digest: str, result: Rendered, epoch: int) -> None:
    with CACHE_LOCK:
        if epoch != cache_epoch:
            return
        size = len(result.html.encode()) + len(result.pdf)
        if size > CACHE_BYTES:
            return
        CACHE[digest] = (time.monotonic() + CACHE_TTL, result)
        while (
            len(CACHE) > 8
            or sum(len(value.html.encode()) + len(value.pdf) for _, value in CACHE.values())
            > CACHE_BYTES
        ):
            CACHE.popitem(last=False)


def template_for(document: ResumeDocument) -> TemplateInfo:
    custom = document.metadata.custom_template
    if custom:
        base = next(t for t in TEMPLATES if t.builtin_key == custom.base)
        styles = base.default_styles.model_copy(update=custom.styles.model_dump(exclude_none=True))
        return TemplateInfo(
            id=document.metadata.template_id,
            name=custom.name,
            builtin_key=custom.base,
            ats_safe=False,
            default_styles=styles,
        )
    return next(t for t in TEMPLATES if t.id == document.metadata.template_id)


def html(document: ResumeDocument) -> str:
    template = template_for(document)
    styles = template.default_styles.model_dump()
    styles.update(document.metadata.style_overrides.model_dump(exclude_none=True))
    font = "ResumeFont"
    margin = styles["margin_mm"]
    css = f"""
    @page {{ size: A4; margin: {margin}mm; }}
    * {{ box-sizing: border-box; }}
    html {{ background: white; color: #202020; }}
    body {{ margin: 0; font-family: {font}; font-size: {styles["font_size_pt"]}pt;
      line-height: {styles["line_height"]}; overflow-wrap: anywhere;
      -webkit-print-color-adjust: exact; }}
    main {{ width: {210 - float(margin or 18) * 2}mm; margin: 0 auto; }}
    h1 {{ font-size: 24pt; margin: 0 0 2mm; color: {styles["accent_color"]}; }}
    h2 {{ font-size: 12pt; margin: {styles["section_spacing_mm"]}mm 0 2mm;
      color: {styles["accent_color"]}; border-bottom: 1px solid {styles["accent_color"]};
      break-after: avoid; }}
    p {{ margin: 0 0 2mm; white-space: pre-wrap; }}
    article {{ margin: 0 0 3mm; }}
    .facts {{ font-weight: bold; break-after: avoid; }}
    .contact {{ font-size: 9pt; margin-bottom: 4mm; }}
    .bullet {{ padding-left: 4mm; position: relative; }}
    .bullet::before {{ content: '•'; position: absolute; left: 0; }}
    a {{ color: inherit; text-decoration: none; }}
    @media screen {{ body {{ padding: {margin}mm 0; }} }}
    """
    if template.builtin_key == "modern":
        css += (
            "h1 { text-transform: uppercase; letter-spacing: .03em; } "
            "h2 { text-transform: uppercase; font-size: 10pt; letter-spacing: .08em; }"
        )
    css += font_css(str(styles["font_family"]))
    custom = document.metadata.custom_template
    if custom:
        validate_template(custom.html, custom.css, {UUID(k) for k in custom.assets})
        css += custom.css + "img{max-width:30mm;max-height:20mm}"
    header = document.header
    contact = [escape(v) for v in [header.email, header.phone, header.location] if v]
    contact += [
        f'<a href="{escape(str(link.url), quote=True)}">'
        f"{escape(link.label)}: {escape(str(link.url))}</a>"
        for link in header.links
    ]
    parts = [
        f"<header><h1>{escape(header.name)}</h1>"
        f"<p class='contact'>{' · '.join(contact)}</p></header>"
    ]
    for section in document.sections:
        if not section.visible:
            continue
        parts.append(f"<section><h2>{escape(section.title)}</h2>")
        previous_facts = None
        for item in section.items:
            parts.append("<article>")
            if item.facts and item.facts != previous_facts:
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
                parts.append(f"<p class='facts'>{' · '.join(escape(v) for v in values if v)}</p>")
            previous_facts = item.facts
            cls = (
                "bullet"
                if section.type in {"experience", "projects"} and not item.experience_summary
                else "text"
            )
            parts.append(f"<p class='{cls}'>{escape(item.text)}</p></article>")
        parts.append("</section>")
    body = "".join(parts)
    if custom:
        body = custom.html.replace("{{header}}", parts[0]).replace(
            "{{sections}}", "".join(parts[1:])
        )
        for identifier, ciphertext in custom.assets.items():
            asset = decrypt_asset(ciphertext, custom.owner_id, UUID(identifier))
            body = body.replace(
                "asset:" + identifier, "data:image/png;base64," + base64.b64encode(asset).decode()
            )
    csp = (
        "default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:; "
        "script-src 'none'; base-uri 'none'; form-action 'none'"
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<meta http-equiv="Content-Security-Policy" content="{csp}">'
        f"<title>{escape(header.name)} resume</title><style>{css}</style></head>"
        f"<body><main>{body}</main></body></html>"
    )


def render(document: ResumeDocument) -> Rendered:
    with CACHE_LOCK:
        epoch = cache_epoch
    artifact = html(document)
    digest = hashlib.sha256(artifact.encode()).hexdigest()
    if result := cached(digest):
        return result
    if not RENDER_LIMIT.acquire(timeout=5):
        raise RendererBusy("PDF renderer is busy. Retry shortly.")
    try:
        if result := cached(digest):
            return result
        result = print_artifact(artifact, digest)
        retain(digest, result, epoch)
        return result
    finally:
        RENDER_LIMIT.release()


def print_artifact(artifact: str, digest: str) -> Rendered:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            context = browser.new_context(java_script_enabled=False, offline=True)
            context.route("**/*", lambda route: route.abort())
            page = context.new_page()
            page.set_default_timeout(15000)
            page.set_content(artifact, wait_until="load")
            page.emulate_media(media="print")
            page.evaluate("document.fonts.ready")
            pdf = page.pdf(prefer_css_page_size=True, print_background=True)
        finally:
            browser.close()
    return Rendered(
        artifact,
        pdf,
        len(PdfReader(BytesIO(pdf)).pages),
        digest,
    )


RendererError = Error
