import re
from html.parser import HTMLParser
from uuid import UUID

from fastapi import HTTPException


class SafeHTML(HTMLParser):
    def __init__(self, assets: set[UUID]) -> None:
        super().__init__(convert_charrefs=True)
        self.assets = assets
        self.stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in {"main", "div", "section", "header", "footer", "p", "span", "img"}:
            raise ValueError("Unsupported HTML tag")
        if len({k for k, v in attrs}) != len(attrs):
            raise ValueError("Duplicate HTML attributes")
        for name, value in attrs:
            if value and any(marker in value for marker in ("{{", "}}", "&", "<", ">")):
                raise ValueError("Template attributes cannot contain placeholders or markup")
            if name == "class" and value and re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{0,30}", value):
                continue
            if tag == "img" and name == "src" and value and value.startswith("asset:"):
                if UUID(value[6:]) in self.assets:
                    continue
            if tag == "img" and name == "alt" and value is not None and len(value) <= 120:
                continue
            raise ValueError("Unsupported attribute or asset")
        if tag == "img":
            if set(dict(attrs)) != {"src", "alt"}:
                raise ValueError("Images need a selected local asset and alt text")
        else:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack or self.stack.pop() != tag:
            raise ValueError("Unbalanced template tags")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "img":
            raise ValueError("Only images may be self-closing")
        self.handle_starttag(tag, attrs)

    def handle_decl(self, decl: str) -> None:
        raise ValueError("Document declarations are unsupported")

    def handle_data(self, data: str) -> None:
        if data.replace("{{header}}", "").replace("{{sections}}", "").strip():
            raise ValueError("Template text must come from content placeholders")

    def handle_comment(self, data: str) -> None:
        raise ValueError("Template comments are unsupported")

    def handle_pi(self, data: str) -> None:
        raise ValueError("Processing instructions are unsupported")


def validate(html: str, css: str, assets: set[UUID]) -> list[str]:
    try:
        if html.count("{{header}}") != 1 or html.count("{{sections}}") != 1:
            raise ValueError("Use exactly one header and one sections placeholder")
        residual = html.replace("{{header}}", "").replace("{{sections}}", "")
        if any(value in residual for value in ("{{", "}}", "{%", "<!", "<?")):
            raise ValueError("Only fixed placeholders are supported")
        parser = SafeHTML(assets)
        parser.feed(html)
        parser.close()
        if parser.stack:
            raise ValueError("Unclosed template tags")
        # Complete token consumption rejects imports, URLs, expressions and hidden rules.
        blocks = list(re.finditer(r"([a-zA-Z0-9 .,_-]+)\{([^{}]*)\}", css))
        if re.sub(r"[a-zA-Z0-9 .,_-]+\{[^{}]*\}", "", css).strip():
            raise ValueError("Unsupported CSS syntax")
        for block in blocks:
            declarations: dict[str, str] = {}
            selectors = [s.strip() for s in block[1].split(",")]
            if any(
                s
                not in {
                    "main",
                    "header",
                    "section",
                    "article",
                    "h1",
                    "h2",
                    "p",
                    ".contact",
                    ".facts",
                    ".text",
                    ".bullet",
                    "img",
                }
                for s in selectors
            ):
                raise ValueError("Unsupported selector")
            for declaration in block[2].split(";"):
                if not declaration.strip():
                    continue
                name, value = [v.strip() for v in declaration.split(":", 1)]
                declarations[name] = value
                if name in {"color", "background-color"} and re.fullmatch(
                    r"#[0-9a-fA-F]{6}", value
                ):
                    continue
                if name == "text-align" and value in {"left", "center"}:
                    continue
                if name == "font-weight" and value in {"400", "600", "700"}:
                    continue
                if (
                    name
                    in {"margin-top", "margin-bottom", "padding-top", "padding-bottom", "width"}
                    and re.fullmatch(r"\d{1,3}(?:\.\d)?mm", value)
                    and 0 <= float(value[:-2]) <= (170 if name == "width" else 15)
                ):
                    continue
                if (
                    name == "font-size"
                    and re.fullmatch(r"\d{1,2}(?:\.\d)?pt", value)
                    and 9 <= float(value[:-2]) <= 24
                ):
                    continue
                raise ValueError("Unsupported or out-of-bounds CSS property")
            if "color" in declarations or "background-color" in declarations:
                foreground = declarations.get("color", "#202020")
                background = declarations.get("background-color", "#ffffff")
                if contrast(foreground, background) < 4.5:
                    raise ValueError("Text/background contrast must be at least 4.5:1")
    except (ValueError, TypeError) as error:
        raise HTTPException(422, "Unsafe or unsupported template: " + str(error)) from error
    warnings = ["ATS compatibility is heuristic; inspect actual extracted text and reading order."]
    if assets:
        warnings.append("Decorative assets may reduce ATS compatibility and do not export to DOCX.")
    if "background-color" in css or "color" in css:
        warnings.append("Check text/background contrast visually before use.")
    return warnings


def contrast(first: str, second: str) -> float:
    def luminance(color: str) -> float:
        values = [int(color[n : n + 2], 16) / 255 for n in (1, 3, 5)]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values]
        return sum(a * b for a, b in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))

    high, low = sorted([luminance(first), luminance(second)], reverse=True)
    return (high + 0.05) / (low + 0.05)
