import pytest

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.constants import REF_PREFIX
from fastapi.testclient import TestClient
from pydantic import BaseModel

from fastapi_validation_override import override_validation_error

PROBLEM_JSON = "application/problem+json"


class Item(BaseModel):  # pragma: no cover
    name: str


class Problem(BaseModel):  # pragma: no cover
    type: str = "about:blank"
    title: str
    status: int
    detail: str


class OutOfStock(BaseModel):  # pragma: no cover
    item_name: str


def build_problem(_request: Request, exc: RequestValidationError) -> Problem:
    return Problem(title="Validation failed", status=400, detail=f"{len(exc.errors())} invalid field(s)")


def test_built_body_is_sent_and_documented_under_media_type() -> None:
    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item) -> None: ...

    override_validation_error(app, error_builder=build_problem, media_type=PROBLEM_JSON)

    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
        response = client.post("/items", json={})

    assert response.status_code == 400
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json() == {
        "type": "about:blank",
        "title": "Validation failed",
        "status": 400,
        "detail": "1 invalid field(s)",
    }
    assert schema["paths"]["/items"]["post"]["responses"]["400"]["content"] == {
        PROBLEM_JSON: {"schema": {"$ref": f"{REF_PREFIX}Problem"}}
    }


def test_default_body_is_sent_and_documented_under_media_type() -> None:
    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item) -> None: ...

    override_validation_error(app, media_type=PROBLEM_JSON)

    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
        response = client.post("/items", json={})

    assert response.headers["content-type"] == PROBLEM_JSON
    assert set(response.json()) == {"detail"}
    assert schema["paths"]["/items"]["post"]["responses"]["400"]["content"] == {
        PROBLEM_JSON: {"schema": {"$ref": f"{REF_PREFIX}HTTPValidationError"}}
    }


def test_existing_response_under_another_media_type_is_kept_alongside() -> None:
    app = FastAPI()

    @app.post("/items", responses={400: {"model": OutOfStock, "description": "Out of stock"}})
    async def create_item(item: Item) -> None: ...

    override_validation_error(app, error_builder=build_problem, media_type=PROBLEM_JSON)

    response_400 = app.openapi()["paths"]["/items"]["post"]["responses"]["400"]

    assert response_400["content"] == {
        "application/json": {"schema": {"$ref": f"{REF_PREFIX}OutOfStock"}},
        PROBLEM_JSON: {"schema": {"$ref": f"{REF_PREFIX}Problem"}},
    }
    assert response_400["description"] == "Out of stock / Validation Error"


def test_existing_response_under_the_same_media_type_is_merged_with_any_of() -> None:
    app = FastAPI()

    @app.post(
        "/items",
        responses={
            400: {
                "description": "Out of stock",
                "content": {PROBLEM_JSON: {"schema": {"$ref": f"{REF_PREFIX}OutOfStock"}}},
            }
        },
    )
    async def create_item(item: Item) -> OutOfStock: ...  # registers the OutOfStock component the $ref above needs

    override_validation_error(app, error_builder=build_problem, media_type=PROBLEM_JSON)

    content = app.openapi()["paths"]["/items"]["post"]["responses"]["400"]["content"]

    assert content[PROBLEM_JSON]["schema"] == {
        "anyOf": [{"$ref": f"{REF_PREFIX}Problem"}, {"$ref": f"{REF_PREFIX}OutOfStock"}]
    }


def test_handle_exceptions_false_documents_media_type_only() -> None:
    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item) -> None: ...

    override_validation_error(app, handle_exceptions=False, media_type=PROBLEM_JSON)

    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
        response = client.post("/items", json={})

    assert set(schema["paths"]["/items"]["post"]["responses"]["400"]["content"]) == {PROBLEM_JSON}
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/json"


def test_status_code_422_with_media_type_is_not_a_no_op() -> None:
    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item) -> None: ...

    override_validation_error(app, status_code=422, media_type=PROBLEM_JSON)

    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
        response = client.post("/items", json={})

    assert response.status_code == 422
    assert response.headers["content-type"] == PROBLEM_JSON
    assert set(schema["paths"]["/items"]["post"]["responses"]["422"]["content"]) == {PROBLEM_JSON}


@pytest.mark.parametrize("media_type", ["text/plain", "application/xml", "application/jsonx", ""])
def test_non_json_media_type_is_rejected(media_type: str) -> None:
    app = FastAPI()

    with pytest.raises(ValueError, match="JSON content type"):
        override_validation_error(app, media_type=media_type)

    assert not getattr(app.state, "_validation_overridden", False)
