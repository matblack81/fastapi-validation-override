"""Builds the raster images of docs/assets/images/: the icons from the SVG logo, and the wordmark.

    uv run python scripts/build_icons.py --channel chrome

The SVG files are the source: logo.svg, favicon.svg (the logo redrawn for small sizes) and
logo-header.svg are edited by hand. This script produces favicon.ico (16, 32 and 48 px),
favicon.png (the file the theme asks for) and apple-touch-icon.png from them, and wordmark.png,
the project name the README shows as its title, set in the site's font. The wordmark needs the
network, to load Roboto from Google Fonts.

Each icon is drawn at eight times its size and scaled down averaging each block of 8 x 8 pixels,
which is exact for a whole-number reduction. Drawing it straight at 16 or 64 px leaves
stair-stepped edges on the diagonals; a sharper filter such as Lanczos adds a halo around them.
"""

import argparse
import io
import struct

from pathlib import Path

from PIL import Image
from playwright.sync_api import Page, sync_playwright

IMAGES = Path(__file__).parent.parent / "docs/assets/images"
SUPERSAMPLE = 8
ICO_SIZES = (16, 32, 48)
WORDMARK_TEXT = "FastAPI Validation Override"
# Indigo 400, a lighter tint of the site's indigo: readable on GitHub's light and dark themes.
WORDMARK_COLOR = "#5c6bc0"
WORDMARK_FONT_SIZE = 128


def square(favicon_svg: str) -> str:
    """The favicon without rounded corners, for iOS, which rounds them itself, and a little
    smaller inside, so the symbol doesn't touch the edge once it does."""
    for expected in (' rx="14"', "scale(1)"):
        if expected not in favicon_svg:
            raise RuntimeError(f"favicon.svg no longer contains {expected!r}: update square() to match it")
    return favicon_svg.replace(' rx="14"', "").replace("scale(1)", "scale(0.88)")


def render(page: Page, svg: str, size: int) -> Image.Image:
    big = size * SUPERSAMPLE
    page.set_viewport_size({"width": big, "height": big})
    page.set_content(
        f'<body style="margin:0;background:transparent"><div style="width:{big}px;height:{big}px">{svg}</div></body>'
        f"<style>svg{{width:{big}px;height:{big}px;display:block}}</style>"
    )
    png = page.screenshot(omit_background=True, clip={"x": 0, "y": 0, "width": big, "height": big})
    return Image.open(io.BytesIO(png)).convert("RGBA").resize((size, size), Image.Resampling.BOX)


def render_wordmark(page: Page) -> Image.Image:
    """The project name in Roboto Bold, cropped to the text, on a transparent background."""
    page.set_viewport_size({"width": 2400, "height": 400})
    page.set_content(
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Roboto:wght@700&display=block">'
        '<body style="margin:0;background:transparent">'
        f'<span id="wordmark" style="font:700 {WORDMARK_FONT_SIZE}px Roboto;color:{WORDMARK_COLOR};'
        # The padding keeps the glyphs inside the screenshot; the crop below removes it
        f'white-space:nowrap;display:inline-block;padding:32px">{WORDMARK_TEXT}</span></body>'
    )
    page.evaluate("document.fonts.ready")
    if not page.evaluate("document.fonts.check('700 16px Roboto')"):
        raise RuntimeError("Roboto didn't load: the wordmark needs the network to reach Google Fonts")
    png = page.locator("#wordmark").screenshot(omit_background=True)
    image = Image.open(io.BytesIO(png)).convert("RGBA")
    return image.crop(image.getbbox())


def write_ico(path: Path, images: list[Image.Image]) -> None:
    blobs = []
    for image in images:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        blobs.append(buffer.getvalue())
    offset = 6 + 16 * len(images)
    entries = b""
    for image, blob in zip(images, blobs, strict=True):
        entries += struct.pack("<BBBBHHII", image.width, image.height, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    path.write_bytes(struct.pack("<HHH", 0, 1, len(images)) + entries + b"".join(blobs))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--channel", help="installed browser to use: chrome or msedge (default: Playwright's Chromium)")
    args = parser.parse_args()

    favicon_svg = (IMAGES / "favicon.svg").read_text(encoding="utf-8")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=args.channel)
        page = browser.new_page()
        ico = [render(page, favicon_svg, size) for size in ICO_SIZES]
        favicon_png = render(page, favicon_svg, 64)
        touch = render(page, square(favicon_svg), 180)
        wordmark = render_wordmark(page)
        browser.close()

    write_ico(IMAGES / "favicon.ico", ico)
    favicon_png.save(IMAGES / "favicon.png", optimize=True)
    touch.convert("RGB").save(IMAGES / "apple-touch-icon.png", optimize=True)
    wordmark.save(IMAGES / "wordmark.png", optimize=True)
    for name in ("favicon.ico", "favicon.png", "apple-touch-icon.png", "wordmark.png"):
        print(f"{name:22} {(IMAGES / name).stat().st_size:6} B")


if __name__ == "__main__":
    main()
