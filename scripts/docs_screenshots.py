"""Regenerates the screenshots of docs/assets/screenshots/ from the apps the pages describe.

    uv run python scripts/docs_screenshots.py --channel chrome
    uv run python scripts/docs_screenshots.py --channel chrome --only media-type-json

Each screenshot is taken in a real browser, from a file of docs_src/ served locally: the same
code the page shows. Swagger UI and ReDoc load their scripts from a CDN, so the machine needs
network access.

--channel chrome (or msedge) uses the browser already installed. Without it, Playwright uses its
own Chromium, installed once with `uv run playwright install chromium`.
"""

import argparse
import importlib.util
import re
import socket
import threading
import time

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import uvicorn

from playwright.sync_api import Locator, Page, sync_playwright

ROOT = Path(__file__).parent.parent
OUT = ROOT / "docs/assets/screenshots"
WIDTH = 800
REDOC_WIDTH = 1000  # ReDoc hides its side menu on narrower windows
SCALE = 2  # screenshots are taken at twice the size they are shown at, to stay sharp on dense screens
PADDING = 16  # left and right of the element, so its text doesn't touch the border of the image


def swagger_responses(page: Page, operation: str) -> Locator:
    """The responses table of one operation, expanded, in Swagger UI."""
    block = page.locator(".opblock", has=page.locator(".opblock-summary-path", has_text=re.compile(f"^{operation}$")))
    block.locator(".opblock-summary").click()
    responses = block.locator(".responses-wrapper")
    responses.wait_for()
    return responses


def swagger_response_with_media_type(page: Page, operation: str, code: str, media_type: str) -> Locator:
    """One response row of an operation in Swagger UI, showing the example of `media_type`."""
    row = swagger_responses(page, operation).locator(f"tr.response[data-code='{code}']")
    row.locator("select").select_option(media_type)
    return row


def redoc_response(page: Page, code: str) -> Locator:
    """The schema of one response, expanded, in ReDoc's middle column."""
    button = page.get_by_role("button", name=re.compile(f"^{code} "))
    button.click()
    return button.locator("xpath=..")


@dataclass(frozen=True)
class Shot:
    name: str
    app: str  # file with an `app`, relative to the repository root
    path: str
    width: int
    target: Callable[[Page], Locator]
    # Swagger UI draws the example box of the previous response over the top edge of a row
    trim_top: int = 0


SHOTS = [
    Shot(
        "quickstart-responses",
        "docs_src/quickstart/basic.py",
        "/docs",
        WIDTH,
        lambda page: swagger_responses(page, "/items"),
    ),
    Shot(
        "media-type-json",
        "docs_src/options/media_type.py",
        "/docs",
        WIDTH,
        lambda page: swagger_response_with_media_type(page, "/orders", "400", "application/json"),
        trim_top=4,
    ),
    Shot(
        "media-type-problem-json",
        "docs_src/options/media_type.py",
        "/docs",
        WIDTH,
        lambda page: swagger_response_with_media_type(page, "/orders", "400", "application/problem+json"),
        trim_top=4,
    ),
    Shot(
        "merge-redoc",
        "docs_src/options/merging.py",
        "/redoc",
        REDOC_WIDTH,
        lambda page: redoc_response(page, "400"),
    ),
]


def take(page: Page, element: Locator, target: Path, trim_top: int) -> None:
    element.scroll_into_view_if_needed()
    box = element.bounding_box()
    if box is None:
        raise RuntimeError(f"Nothing to capture for {target.name}: the element isn't visible")
    scroll_y = page.evaluate("scrollY")
    clip = {
        "x": max(box["x"] - PADDING, 0),
        "y": box["y"] + scroll_y + trim_top,
        "width": box["width"] + 2 * PADDING,
        "height": box["height"] - trim_top,
    }
    page.screenshot(path=target, type="jpeg", quality=88, clip=clip, full_page=True)


def load_app(relative: str) -> Any:
    spec = importlib.util.spec_from_file_location(f"shot_{relative.replace('/', '_')}", ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {relative}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


@contextmanager
def serve(app: Any) -> Iterator[str]:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--channel", help="installed browser to use: chrome or msedge (default: Playwright's Chromium)")
    parser.add_argument("--only", nargs="+", metavar="NAME", help="take only these screenshots")
    args = parser.parse_args()

    shots = [shot for shot in SHOTS if not args.only or shot.name in args.only]
    unknown = set(args.only or []) - {shot.name for shot in SHOTS}
    if unknown:
        parser.error(f"unknown screenshot(s): {', '.join(sorted(unknown))}")

    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=args.channel)
        context = browser.new_context(device_scale_factor=SCALE, color_scheme="light")
        page = context.new_page()
        for app_file in dict.fromkeys(shot.app for shot in shots):
            with serve(load_app(app_file)) as base_url:
                for shot in (s for s in shots if s.app == app_file):
                    page.set_viewport_size({"width": shot.width, "height": 900})
                    page.goto(f"{base_url}{shot.path}", wait_until="networkidle")
                    target = OUT / f"{shot.name}.jpg"
                    take(page, shot.target(page), target, shot.trim_top)
                    print(f"{shot.name:26} {target.stat().st_size // 1024:4} KB  <- {shot.app} {shot.path}")
        browser.close()


if __name__ == "__main__":
    main()
