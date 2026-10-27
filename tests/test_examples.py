"""Smoke tests for examples/: each file should import cleanly and produce a valid OpenAPI schema."""

import importlib.util

from pathlib import Path
from typing import Any

import fastapi.openapi.utils as fastapi_openapi_utils
import pytest

from fastapi import FastAPI
from inline_snapshot import snapshot

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
EXAMPLE_FILES = sorted(EXAMPLES_DIR.glob("*.py"))

# For each example: the response codes of every operation (paths, webhooks, callbacks) and the
# validation error components. Only what the package decides, so it holds across the whole
# FastAPI matrix. Regenerate with `pytest tests/test_examples.py --fix` and read the diff:
# `--inline-snapshot=fix` alone corrects existing entries but doesn't add a new example's.
SCHEMAS = snapshot(
    {
        "basic": {
            "paths": {"/items": {"post": ["200", "400"]}},
            "components": ["HTTPValidationError", "ValidationError"],
        },
        "custom_422_response": {
            "paths": {"/items": {"post": ["200", "400", "422"]}},
            "components": ["HTTPValidationError", "ValidationError"],
        },
        "custom_openapi": {
            "paths": {"/items": {"post": ["200", "400"]}},
            "components": ["HTTPValidationError", "ValidationError"],
        },
        "custom_status_code": {
            "paths": {"/items": {"post": ["200", "409"]}},
            "components": ["HTTPValidationError", "ValidationError"],
        },
        "custom_validation_schema": {
            "paths": {"/items": {"post": ["200", "400"]}},
            "components": ["HTTPValidationError", "ValidationError"],
        },
        "error_builder": {
            "paths": {"/items": {"post": ["200", "400"]}, "/health": {"get": ["200"]}},
            "components": [],
        },
        "existing_response_at_target_code": {
            "paths": {"/items": {"post": ["200", "400"]}},
            "components": ["HTTPValidationError", "ValidationError"],
        },
        "handle_exceptions_false": {
            "paths": {"/items": {"post": ["200", "400"]}},
            "components": ["HTTPValidationError", "ValidationError"],
        },
        "webhooks_and_callbacks": {
            "paths": {"/items": {"post": ["200", "400"]}},
            "webhooks": {"item-created": {"post": ["200", "400"]}},
            "callbacks": {"item_updated_callback": {"{$callback_url}/updated": {"post": ["200", "400"]}}},
            "components": ["HTTPValidationError", "ValidationError"],
        },
        "with_apirouter": {
            "paths": {"/items": {"post": ["200", "400"]}, "/users": {"post": ["200", "400"]}},
            "components": ["HTTPValidationError", "ValidationError"],
        },
    }
)


def _response_codes(path_items: dict[str, Any]) -> dict[str, dict[str, list[str]]]:
    return {
        path: {method: sorted(operation["responses"]) for method, operation in item.items()}
        for path, item in path_items.items()
    }


def _project(schema: dict[str, Any]) -> dict[str, Any]:
    projection: dict[str, Any] = {"paths": _response_codes(schema["paths"])}
    if "webhooks" in schema:
        projection["webhooks"] = _response_codes(schema["webhooks"])
    callbacks = {
        name: _response_codes(path_items)
        for item in schema["paths"].values()
        for operation in item.values()
        for name, path_items in operation.get("callbacks", {}).items()
    }
    if callbacks:
        projection["callbacks"] = callbacks
    projection["components"] = sorted(
        name for name in schema["components"]["schemas"] if name.endswith("ValidationError")
    )
    return projection


@pytest.mark.parametrize("example_file", EXAMPLE_FILES, ids=lambda path: path.stem)
def test_example_imports_and_generates_openapi_schema(example_file: Path) -> None:
    # custom_validation_schema.py reassigns these at module level without restoring them; save and
    # restore around every example so import order can never leak state into other tests.
    original_validation_error = fastapi_openapi_utils.validation_error_definition
    original_http_validation_error = fastapi_openapi_utils.validation_error_response_definition

    spec = importlib.util.spec_from_file_location(example_file.stem, example_file)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
    finally:
        fastapi_openapi_utils.validation_error_definition = original_validation_error
        fastapi_openapi_utils.validation_error_response_definition = original_http_validation_error

    assert isinstance(module.app, FastAPI)
    schema = module.app.openapi()
    assert isinstance(schema, dict)
    assert _project(schema) == SCHEMAS[example_file.stem]
