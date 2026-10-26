"""Sync/check the portable UI kit, documented tokens and principal contrast pairs.

Check/sync read local source only. Browser mode serves the public reference on
loopback; no application configuration, database, remote network or model calls.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "frontend/src/styles"
STARTER = ROOT / "docs/design/ui-starter"
GUIDE = ROOT / "docs/design/UI_UX_STYLE_GUIDE.md"
ASSETS = ("tokens.css", "foundation.css")
VERSION = "1.0.0"
START = "<!-- ui-tokens:start -->"
END = "<!-- ui-tokens:end -->"


def browser_check() -> None:
    """Exercise the distributed reference site, isolated from all product services/data."""
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread

    from playwright.sync_api import expect, sync_playwright

    evidence = ROOT / ".validation"
    evidence.mkdir(exist_ok=True)
    errors: list[str] = []
    external: list[str] = []

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

    with ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(Handler, directory=str(STARTER.parent))
    ) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    page = browser.new_page(viewport={"width": 1440, "height": 1000})
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on(
                        "request",
                        lambda request: (
                            external.append(request.url)
                            if not request.url.startswith(base + "/")
                            else None
                        ),
                    )
                    page.goto(base + "/ui-starter/")
                    expect(page.locator("main h1")).to_be_visible()
                    page.get_by_label("Project name", exact=True).fill("Preserved example draft")
                    page.get_by_role("tab", name="Content", exact=True).focus()
                    page.keyboard.press("ArrowRight")
                    expect(page.get_by_role("tab", name="Appearance")).to_be_focused()
                    expect(page.get_by_label("Project name", exact=True)).to_be_hidden()
                    page.keyboard.press("Home")
                    expect(page.get_by_label("Project name", exact=True)).to_have_value(
                        "Preserved example draft"
                    )
                    page.get_by_role("button", name="Save changes", exact=True).click()
                    expect(page.locator("[data-save-status]")).to_have_text(
                        "Example saved in this page only. No server request was made."
                    )
                    summary = page.locator("details.disclosure summary")
                    summary.click()
                    page.keyboard.press("Escape")
                    expect(page.locator("details.disclosure")).not_to_have_attribute("open", "")
                    expect(summary).to_be_focused()
                    for width in (320, 390, 768, 1280, 1440):
                        page.set_viewport_size({"width": width, "height": 1000})
                        assert not page.evaluate(
                            "document.documentElement.scrollWidth > innerWidth"
                        ), f"Reference site overflow at {width}"
                        assert page.locator("button, .button").evaluate_all(
                            "elements => elements.filter(e => e.getBoundingClientRect().width)"
                            ".every(e => e.getBoundingClientRect().height >= 44)"
                        ), "Reference control below target height"
                        page.screenshot(
                            path=str(evidence / f"ui-style-reference-{width}.png"), full_page=True
                        )
                    page.emulate_media(reduced_motion="reduce", forced_colors="active")
                    page.screenshot(
                        path=str(evidence / "ui-style-reference-forced-colors.png"), full_page=True
                    )
                    assert not errors and not external, (errors, external)
                    (evidence / "ui-style-reference-evidence.json").write_text(
                        json.dumps(
                            {
                                "passed": True,
                                "style_version": VERSION,
                                "browser": browser.version,
                                "viewports": [320, 390, 768, 1280, 1440],
                                "draft_preserved": True,
                                "errors": errors,
                                "external": external,
                            },
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                finally:
                    browser.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
    print("PASS: distributed UI reference, keyboard/drafts, targets and responsive screenshots")


def luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return sum(
        value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "sync", "browser"), default="check", nargs="?")
    mode = parser.parse_args().mode
    sync = mode == "sync"
    sources = {name: (SOURCE / name).read_text(encoding="utf-8") for name in ASSETS}
    manifest = (
        json.dumps(
            {
                "style_version": VERSION,
                "assets": {
                    name: hashlib.sha256(text.encode()).hexdigest()
                    for name, text in sources.items()
                },
            },
            indent=2,
        )
        + "\n"
    )
    for name, text in {**sources, "manifest.json": manifest}.items():
        target = STARTER / name
        if sync:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="\n")
        elif not target.exists() or target.read_text(encoding="utf-8") != text:
            raise SystemExit(
                f"Portable UI asset drift: {name}; run python scripts/ui_style.py sync"
            )
    guide = GUIDE.read_text(encoding="utf-8")
    before, marker, tail = guide.partition(START)
    _old, end_marker, after = tail.partition(END)
    if not marker or not end_marker:
        raise SystemExit("UI style guide token markers are missing")
    expected = "\n\n```css\n" + sources["tokens.css"].rstrip() + "\n```\n\n"
    if sync:
        GUIDE.write_text(before + START + expected + END + after, encoding="utf-8", newline="\n")
    elif _old != expected:
        raise SystemExit("Documented UI tokens drifted; run python scripts/ui_style.py sync")
    tokens = dict(re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{6})\s*;", sources["tokens.css"]))
    pairs = (
        ("body", "--color-text", "--color-bg", 4.5),
        ("secondary text", "--color-text-muted", "--color-bg", 4.5),
        ("panel secondary text", "--color-text-muted", "--color-surface", 4.5),
        ("primary action", "--color-surface", "--color-action", 4.5),
        ("primary hover", "--color-surface", "--color-action-hover", 4.5),
        ("link", "--color-link", "--color-surface", 4.5),
        ("selected segment", "--color-on-selected", "--color-selected", 4.5),
        ("field boundary", "--color-control-border", "--color-surface", 3),
        ("focus", "--color-focus", "--color-bg", 3),
        ("warning", "--color-warning", "--color-warning-bg", 4.5),
        ("error", "--color-danger", "--color-danger-bg", 4.5),
    )
    for label, foreground, background, minimum in pairs:
        low, high = sorted((luminance(tokens[foreground]), luminance(tokens[background])))
        ratio = (high + 0.05) / (low + 0.05)
        if ratio < minimum:
            raise SystemExit(f"{label} contrast {ratio:.2f}:1 is below {minimum}:1")
    print(f"PASS: UI kit {VERSION}, documented tokens and {len(pairs)} contrast pairs")
    if mode == "browser":
        browser_check()


if __name__ == "__main__":
    main()
