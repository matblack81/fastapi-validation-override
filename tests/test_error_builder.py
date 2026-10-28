from typing import Any

import pytest

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.constants import REF_PREFIX
from fastapi.testclient import TestClient
from pydantic import BaseModel

from fastapi_validation_override import override_validation_error


class Item(BaseModel):  # pragma: no cover
    name: str


class FieldError(BaseModel):  # pragma: no cover
    field: str
    message: str


class ErrorEnvelope(BaseModel):  # pragma: no cover
    code: str = "VALIDATION_ERROR"
    errors: list[FieldError]


class OutOfStock(BaseModel):  # pragma: no cover
    item_name: str


def build_envelope(_request: Request, exc: RequestValidationError) -> ErrorEnvelope:
    return ErrorEnvelope(
        errors=[FieldError(field=".".join(map(str, error["loc"])), message=error["msg"]) for error in exc.errors()]
    )


def test_invalid_request_returns_built_body_at_status_code() -> None:
    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item) -> None: ...

    override_validation_error(app, error_builder=build_envelope)

    with TestClient(app) as client:
        response = client.post("/items", json={})

    assert response.status_code == 400
    assert response.json() == {
        "code": "VALIDATION_ERROR",
        "errors": [{"field": "body.name", "message": "Field required"}],
    }


def test_model_is_documented_only_on_operations_that_validate() -> None:
    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item) -> None: ...

    @app.get("/health")
    async def health() -> None: ...

    override_validation_error(app, error_builder=build_envelope)

    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    items_responses = schema["paths"]["/items"]["post"]["responses"]
    assert set(items_responses) == {"200", "400"}
    assert items_responses["400"]["content"]["application/json"]["schema"] == {"$ref": f"{REF_PREFIX}ErrorEnvelope"}
    assert set(schema["paths"]["/health"]["get"]["responses"]) == {"200"}


def test_model_and_nested_models_replace_fastapi_components() -> None:
    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item) -> None: ...

    override_validation_error(app, error_builder=build_envelope)

    components = app.openapi()["components"]["schemas"]

    assert set(components) == {"Item", "ErrorEnvelope", "FieldError"}
    assert components["ErrorEnvelope"]["properties"]["errors"]["items"] == {"$ref": f"{REF_PREFIX}FieldError"}
    assert set(components["FieldError"]["properties"]) == {"field", "message"}


def test_fastapi_components_still_referenced_are_kept() -> None:
    app = FastAPI()

    @app.post(
        "/items",
        responses={
            418: {
                "description": "Legacy validation error",
                "content": {"application/json": {"schema": {"$ref": f"{REF_PREFIX}HTTPValidationError"}}},
            }
        },
    )
    async def create_item(item: Item) -> None: ...

    override_validation_error(app, error_builder=build_envelope)

    components = app.openapi()["components"]["schemas"]

    assert {"HTTPValidationError", "ValidationError", "ErrorEnvelope", "FieldError"} <= set(components)


def test_model_already_used_by_a_route_is_reused() -> None:
    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item) -> ErrorEnvelope: ...

    override_validation_error(app, error_builder=build_envelope)

    schema = app.openapi()

    responses = schema["paths"]["/items"]["post"]["responses"]
    assert responses["200"]["content"]["application/json"]["schema"] == {"$ref": f"{REF_PREFIX}ErrorEnvelope"}
    assert responses["400"]["content"]["application/json"]["schema"] == {"$ref": f"{REF_PREFIX}ErrorEnvelope"}
    assert set(schema["components"]["schemas"]) == {"Item", "ErrorEnvelope", "FieldError"}


def test_model_name_taken_by_a_different_model_is_namespaced() -> None:
    class ErrorEnvelope(BaseModel):  # pragma: no cover
        message: str

    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item) -> ErrorEnvelope: ...

    override_validation_error(app, error_builder=build_envelope)

    schema = app.openapi()

    components = schema["components"]["schemas"]
    assert set(components["ErrorEnvelope"]["properties"]) == {"message"}
    assert schema["paths"]["/items"]["post"]["responses"]["400"]["content"]["application/json"]["schema"] == {
        "$ref": f"{REF_PREFIX}FastAPIValidationOverride_ErrorEnvelope"
    }
    namespaced_items = components["FastAPIValidationOverride_ErrorEnvelope"]["properties"]["errors"]["items"]
    assert namespaced_items == {"$ref": f"{REF_PREFIX}FastAPIValidationOverride_FieldError"}
    assert set(components["FastAPIValidationOverride_FieldError"]["properties"]) == {"field", "message"}


def test_model_named_like_fastapi_components_takes_their_place() -> None:
    class ValidationError(BaseModel):  # pragma: no cover
        field: str

    class HTTPValidationError(BaseModel):  # pragma: no cover
        errors: list[ValidationError]

    def build(_request: Request, exc: RequestValidationError) -> HTTPValidationError:
        return HTTPValidationError(
            errors=[ValidationError(field=".".join(map(str, error["loc"]))) for error in exc.errors()]
        )

    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item) -> None: ...

    override_validation_error(app, error_builder=build)

    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
        response = client.post("/items", json={})

    assert response.json() == {"errors": [{"field": "body.name"}]}
    components = schema["components"]["schemas"]
    assert set(components) == {"Item", "HTTPValidationError", "ValidationError"}
    assert components["HTTPValidationError"]["properties"]["errors"]["items"] == {
        "$ref": f"{REF_PREFIX}ValidationError"
    }
    assert set(components["ValidationError"]["properties"]) == {"field"}
    assert schema["paths"]["/items"]["post"]["responses"]["400"]["content"]["application/json"]["schema"] == {
        "$ref": f"{REF_PREFIX}HTTPValidationError"
    }


def test_model_is_merged_with_existing_response_at_status_code() -> None:
    app = FastAPI()

    @app.post("/items", responses={400: {"model": OutOfStock, "description": "Out of stock"}})
    async def create_item(item: Item) -> None: ...

    override_validation_error(app, error_builder=build_envelope)

    response_400 = app.openapi()["paths"]["/items"]["post"]["responses"]["400"]

    assert response_400["content"]["application/json"]["schema"] == {
        "anyOf": [{"$ref": f"{REF_PREFIX}ErrorEnvelope"}, {"$ref": f"{REF_PREFIX}OutOfStock"}]
    }
    assert response_400["description"] == "Out of stock / Validation Error"


def test_status_code_422_replaces_the_body_and_the_schema() -> None:
    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item) -> None: ...

    override_validation_error(app, status_code=422, error_builder=build_envelope)

    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
        response = client.post("/items", json={})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    response_422 = schema["paths"]["/items"]["post"]["responses"]["422"]
    assert response_422["content"]["application/json"]["schema"] == {"$ref": f"{REF_PREFIX}ErrorEnvelope"}
    assert "HTTPValidationError" not in schema["components"]["schemas"]


def test_self_referencing_model_is_registered_as_its_definition() -> None:
    class Problem(BaseModel):  # pragma: no cover
        detail: str
        causes: list["Problem"] = []

    def build_problem(_request: Request, exc: RequestValidationError) -> Problem:
        return Problem(detail="invalid", causes=[Problem(detail=error["msg"]) for error in exc.errors()])

    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item) -> None: ...

    override_validation_error(app, error_builder=build_problem)

    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
        response = client.post("/items", json={})

    problem = schema["components"]["schemas"]["Problem"]
    assert problem["properties"]["causes"]["items"] == {"$ref": f"{REF_PREFIX}Problem"}
    assert "$ref" not in problem
    assert response.json() == {"detail": "invalid", "causes": [{"detail": "Field required", "causes": []}]}


def test_schema_is_stable_across_openapi_calls() -> None:
    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item) -> None: ...

    override_validation_error(app, error_builder=build_envelope)

    first = app.openapi()
    app.openapi_schema = None
    second = app.openapi()

    assert second == first
    assert set(second["components"]["schemas"]) == {"Item", "ErrorEnvelope", "FieldError"}


def no_annotation(_request, exc):  # type: ignore[no-untyped-def]
    ...


def returns_dict(_request: Request, exc: RequestValidationError) -> dict[str, Any]: ...


def returns_none(_request: Request, exc: RequestValidationError) -> None: ...


@pytest.mark.parametrize("builder", [no_annotation, returns_dict, returns_none])
def test_builder_without_a_model_return_type_is_rejected(builder: Any) -> None:
    app = FastAPI()

    with pytest.raises(TypeError, match="Pydantic model as its return type"):
        override_validation_error(app, error_builder=builder)

    assert not getattr(app.state, "_validation_overridden", False)


def test_async_builder_is_awaited() -> None:
    async def build(request: Request, exc: RequestValidationError) -> ErrorEnvelope:
        return build_envelope(request, exc)

    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item) -> None: ...

    override_validation_error(app, error_builder=build)

    with TestClient(app) as client:
        response = client.post("/items", json={})
        schema = client.get("/openapi.json").json()

    assert response.status_code == 400
    assert response.json() == {
        "code": "VALIDATION_ERROR",
        "errors": [{"field": "body.name", "message": "Field required"}],
    }
    assert schema["paths"]["/items"]["post"]["responses"]["400"]["content"]["application/json"]["schema"] == {
        "$ref": f"{REF_PREFIX}ErrorEnvelope"
    }


def test_builder_with_handle_exceptions_false_only_sets_the_documented_model() -> None:
    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item) -> None: ...

    override_validation_error(app, handle_exceptions=False, error_builder=build_envelope)

    with TestClient(app) as client:
        response = client.post("/items", json={})
        schema = client.get("/openapi.json").json()

    assert schema["paths"]["/items"]["post"]["responses"]["400"]["content"]["application/json"]["schema"] == {
        "$ref": f"{REF_PREFIX}ErrorEnvelope"
    }
    assert "HTTPValidationError" not in schema["components"]["schemas"]
    # No handler was registered: FastAPI answers on its own, with its body, not the builder's
    assert response.status_code == 422
    assert set(response.json()) == {"detail"}


class PathEnvelope(BaseModel):  # pragma: no cover
    path: str
    errors: int


def test_builder_taking_the_request_receives_it() -> None:
    def build(request: Request, exc: RequestValidationError) -> PathEnvelope:
        return PathEnvelope(path=request.url.path, errors=len(exc.errors()))

    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item) -> None: ...

    override_validation_error(app, error_builder=build)

    with TestClient(app) as client:
        response = client.post("/items", json={})
        schema = client.get("/openapi.json").json()

    assert response.status_code == 400
    assert response.json() == {"path": "/items", "errors": 1}
    assert schema["paths"]["/items"]["post"]["responses"]["400"]["content"]["application/json"]["schema"] == {
        "$ref": f"{REF_PREFIX}PathEnvelope"
    }


def takes_nothing() -> ErrorEnvelope: ...


def takes_only_the_exception(exc: RequestValidationError) -> ErrorEnvelope: ...


def takes_three(_request: Request, exc: RequestValidationError, extra: int) -> ErrorEnvelope: ...


@pytest.mark.parametrize("builder", [takes_nothing, takes_only_the_exception, takes_three])
def test_builder_that_cant_take_the_request_and_the_exception_is_rejected(builder: Any) -> None:
    app = FastAPI()

    with pytest.raises(TypeError, match="the request and the exception"):
        override_validation_error(app, error_builder=builder)

    assert not getattr(app.state, "_validation_overridden", False)
