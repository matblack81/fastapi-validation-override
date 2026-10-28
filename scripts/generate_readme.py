"""Generates README.md from the docs, so the two can't drift apart.

The README is the page PyPI and GitHub show. Its intro, parameter table, requirements,
installation and first example come from docs/index.md, docs/quickstart.md and
docs_src/quickstart/basic.py; the logo, the badges and the closing links are written here.

    uv run python scripts/generate_readme.py

Like FastAPI's generate-readme, it rewrites README.md and exits with 1 when the file was out of
date, which is what makes the pre-commit hook fail once and pass after the change is staged.
"""

import re
import sys

from pathlib import Path

ROOT = Path(__file__).parent.parent
README = ROOT / "README.md"
SITE_URL = "https://fastapi-validation-override.matblack81.com/"
REPO_URL = "https://github.com/matblack81/fastapi-validation-override"
ASSETS_URL = "https://raw.githubusercontent.com/matblack81/fastapi-validation-override/main/docs/assets/images"

HEADER = f"""<p align="center">
  <img src="{ASSETS_URL}/logo.svg" alt="FastAPI Validation Override logo" width="128">
</p>

<h1 align="center">
  <img src="{ASSETS_URL}/wordmark.png" alt="FastAPI Validation Override" width="525">
</h1>

<p align="center">
  <a href="{REPO_URL}/actions"><img src="{REPO_URL}/workflows/Test/badge.svg" alt="Build Status"></a>
  <a href="https://codecov.io/github/matblack81/fastapi-validation-override"><img src="https://codecov.io/github/matblack81/fastapi-validation-override/graph/badge.svg?token=SL4JPWAB0O" alt="codecov"></a>
  <a href="https://pypi.org/project/fastapi-validation-override/"><img src="https://img.shields.io/pypi/v/fastapi-validation-override?color=%2334D058&label=pypi%20package" alt="pypi package"></a>
  <a href="https://pypi.org/project/fastapi-validation-override/"><img src="https://img.shields.io/pypi/pyversions/fastapi-validation-override.svg?color=%2334D058" alt="Supported Python versions"></a>
  <a href="{REPO_URL}/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT"></a>
</p>
"""

FOOTER = f"""## Release Notes

[RELEASE_NOTES]({REPO_URL}/blob/main/docs/release-notes.md)

---

## License

[MIT]({REPO_URL}/blob/main/LICENSE)
"""


def sections(markdown: str) -> dict[str, list[str]]:
    """The body of each `## ` section, without the blank lines around it. Headings inside code
    fences don't count."""
    found: dict[str, list[str]] = {}
    current: list[str] | None = None
    in_fence = False
    for line in markdown.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("## "):
            current = found.setdefault(line[3:].strip(), [])
        elif current is not None:
            current.append(line)
    return {title: _trim(lines) for title, lines in found.items()}


def _trim(lines: list[str]) -> list[str]:
    start, end = 0, len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def site_links(markdown: str) -> str:
    """Relative links to pages of the site, such as `options/media-type.md#anchor`, as the URLs
    the site serves them at: the README is read on GitHub and PyPI, where they don't resolve."""
    return re.sub(
        r"\]\(([\w/-]+)\.md(#[\w-]+)?\)",
        lambda match: f"]({SITE_URL}{match.group(1)}/{match.group(2) or ''})",
        markdown,
    )


def intro(index: str) -> str:
    """The paragraph that follows the one-line description under the title."""
    lines = index.splitlines()
    tagline = next(i for i, line in enumerate(lines) if 'class="hero-tagline"' in line)
    return next(line for line in lines[tagline + 1 :] if line.strip())


def installation(body: list[str]) -> str:
    """The commands of the pip and uv tabs, in one block."""
    commands = [line[4:] for line in body if line.startswith("    ") and not line.strip().startswith("```")]
    return "```bash\n" + "\n# or\n".join(commands) + "\n```"


def first_paragraph(markdown: str) -> str:
    body = markdown.split("---", 2)[2] if markdown.startswith("---") else markdown
    lines = [line for line in body.splitlines() if not line.startswith("# ")]
    paragraph: list[str] = []
    for line in _trim(lines):
        if not line.strip():
            break
        paragraph.append(line)
    return "\n".join(paragraph)


def generate_readme() -> str:
    index = (ROOT / "docs/index.md").read_text(encoding="utf-8")
    quickstart = (ROOT / "docs/quickstart.md").read_text(encoding="utf-8")
    snippet = (ROOT / "docs_src/quickstart/basic.py").read_text(encoding="utf-8").rstrip("\n")
    parts = sections(index)

    return f"""{HEADER}
{intro(index)}

Documentation: {SITE_URL}

---

## What you can change

{site_links(chr(10).join(parts["What you can change"]))}

---

## Requirements

{chr(10).join(parts["Requirements"])}

---

## Installation

{installation(parts["Installation"])}

---

## Quick start

{first_paragraph(quickstart)}

```python
{snippet}
```

The response, the schema, the other options and the parameter reference are in the [documentation]({SITE_URL}).

---

{FOOTER}"""


def main() -> int:
    new_content = generate_readme()
    old_content = README.read_text(encoding="utf-8")
    if new_content != old_content:
        README.write_text(new_content, encoding="utf-8")
        print("README.md was out of date; it has been regenerated from the docs.")
        return 1
    print("README.md is up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
