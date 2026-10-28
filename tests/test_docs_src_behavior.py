"""What the docs pages say each docs_src file does, checked against the running app."""

import importlib.util

from pathlib import Path
from typing import Any

from fastapi.openapi.constants import REF_PREFIX
from fastapi.testclient import TestClient

DOCS_SRC = Path(__file__).parent.parent / "docs_src"


def load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(f"docs_src_{name.replace('/', '_')}", DOCS_SRC / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_quickstart_returns_and_documents_400_with_fastapi_body() -> None:
    with TestClient(load("quickstart/basic").app) as client:
        invalid = client.post("/items", json={"name": "Hammer"})
        valid = client.post("/items", json={"name": "Hammer", "price": 9.5})
        schema = client.get("/openapi.json").json()

    assert invalid.status_code == 400
    assert invalid.headers["content-type"] == "application/json"
    assert invalid.json() == {
        "detail": [{"type": "missing", "loc": ["body", "price"], "msg": "Field required", "input": {"name": "Hammer"}}]
    }
    assert valid.status_code == 200
    responses = schema["paths"]["/items"]["post"]["responses"]
    assert set(responses) == {"200", "400"}
    assert responses["400"]["content"]["application/json"]["schema"] == {"$ref": f"{REF_PREFIX}HTTPValidationError"}


def test_quickstart_status_code_returns_and_documents_409() -> None:
    with TestClient(load("quickstart/status_code").app) as client:
        invalid = client.post("/items", json={"name": "Hammer"})
        schema = client.get("/openapi.json").json()

    assert invalid.status_code == 409
    assert set(invalid.json()) == {"detail"}
    assert set(schema["paths"]["/items"]["post"]["responses"]) == {"200", "409"}
