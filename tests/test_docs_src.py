import importlib.util
import re

from pathlib import Path
from typing import Any

import pytest

from fastapi.testclient import TestClient
from inline_snapshot import snapshot

DOCS_SRC = Path(__file__).parent.parent / "docs_src"
SNIPPETS = sorted(DOCS_SRC.rglob("*.py"))

# For each docs_src file: the response codes of every operation and the validation error
# components. Only what the package decides, so it holds across the whole FastAPI matrix.
# Regenerate with `pytest tests/test_docs_src.py --fix` and read the diff:
# `--inline-snapshot=fix` alone corrects existing entries but doesn't add a new file's.
SCHEMAS = snapshot(
    {
        "quickstart/basic": {
            "paths": {"/items": {"post": ["200", "400"]}},
            "components": ["HTTPValidationError", "ValidationError"],
        },
        "quickstart/status_code": {
            "paths": {"/items": {"post": ["200", "409"]}},
            "components": ["HTTPValidationError", "ValidationError"],
        },
        "options/custom_422": {
            "paths": {"/items": {"post": ["200", "400", "422"]}},
            "components": ["HTTPValidationError", "ValidationError"],
        },
        "options/custom_openapi": {
            "paths": {"/items": {"post": ["200", "400"]}},
            "components": ["HTTPValidationError", "ValidationError"],
        },
        "options/error_builder": {
            "paths": {"/items": {"post": ["200", "400"]}, "/health": {"get": ["200"]}},
            "components": [],
        },
        "options/exception_handler": {
            "paths": {"/items": {"post": ["200", "400"]}},
            "components": ["HTTPValidationError", "ValidationError"],
        },
        "options/media_type": {"paths": {"/orders": {"post": ["200", "400"]}}, "components": []},
        "options/merging": {
            "paths": {"/items": {"post": ["200", "400"]}},
            "components": ["HTTPValidationError", "ValidationError"],
        },
        "options/merging_disabled": {
            "paths": {"/items": {"post": ["200", "400"]}},
            "components": ["HTTPValidationError", "ValidationError"],
        },
        "options/patch_422_responses": {
            "paths": {"/items": {"post": ["200", "422"]}},
            "components": ["HTTPValidationError", "ValidationError"],
        },
        "options/sub_app": {
            "paths": {"/items": {"post": ["200", "422"]}},
            "components": ["HTTPValidationError", "ValidationError"],
        },
        "options/webhooks_and_callbacks": {
            "paths": {"/items": {"post": ["200", "400"]}},
            "components": ["HTTPValidationError", "ValidationError"],
        },
        "options/error_builder_handler": {"paths": {"/items": {"post": ["200", "400"]}}, "components": []},
        "options/error_builder_request": {"paths": {"/items": {"post": ["200", "400"]}}, "components": []},
    }
)


def snippet_id(path: Path) -> str:
    return path.relative_to(DOCS_SRC).with_suffix("").as_posix()


def _project(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "paths": {
            path: {method: sorted(operation["responses"]) for method, operation in item.items()}
            for path, item in schema["paths"].items()
        },
        "components": sorted(
            name for name in schema.get("components", {}).get("schemas", {}) if name.endswith("ValidationError")
        ),
    }


@pytest.mark.parametrize("snippet", SNIPPETS, ids=snippet_id)
def test_docs_snippet_runs_and_documents_its_validation_error(snippet: Path) -> None:
    """The docs pages include these files, so a page can't show code that no longer runs."""
    spec = importlib.util.spec_from_file_location(f"docs_src_{snippet.stem}", snippet)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    with TestClient(module.app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert _project(response.json()) == SCHEMAS[snippet_id(snippet)]


def pages_text() -> str:
    return "\n".join(page.read_text(encoding="utf-8") for page in (DOCS_SRC.parent / "docs").rglob("*.md"))


def test_every_docs_src_file_is_included_by_a_page() -> None:
    """A file no page includes is an example nobody reads, and nobody notices when it rots."""
    pages = pages_text()

    files = [path.relative_to(DOCS_SRC.parent).as_posix() for path in SNIPPETS]

    assert files
    assert [path for path in files if path not in pages] == []


def test_every_page_include_points_at_an_existing_docs_src_file() -> None:
    included = re.findall(r'--8<-- "(docs_src/[^":]+)', pages_text())

    assert included
    assert [path for path in included if not (DOCS_SRC.parent / path).is_file()] == []
