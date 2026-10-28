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


def ref(name: str) -> dict[str, str]:
    return {"$ref": f"{REF_PREFIX}{name}"}


def test_error_builder_returns_and_documents_the_envelope() -> None:
    with TestClient(load("options/error_builder").app) as client:
        invalid = client.post("/items", json={"name": "Hammer"})
        schema = client.get("/openapi.json").json()

    assert invalid.status_code == 400
    assert invalid.json() == {
        "code": "VALIDATION_ERROR",
        "errors": [{"field": "body.price", "message": "Field required"}],
    }
    assert schema["paths"]["/items"]["post"]["responses"]["400"]["content"] == {
        "application/json": {"schema": ref("ErrorEnvelope")}
    }
    assert set(schema["paths"]["/health"]["get"]["responses"]) == {"200"}
    assert set(schema["components"]["schemas"]) == {"ErrorEnvelope", "FieldError", "Item"}


def test_media_type_sends_problem_json_next_to_the_declared_error() -> None:
    with TestClient(load("options/media_type").app) as client:
        invalid = client.post("/orders", json={"name": "Hammer"})
        schema = client.get("/openapi.json").json()

    assert invalid.status_code == 400
    assert invalid.headers["content-type"] == "application/problem+json"
    assert invalid.json() == {
        "type": "about:blank",
        "title": "Validation failed",
        "status": 400,
        "detail": "1 invalid field(s)",
    }
    response_400 = schema["paths"]["/orders"]["post"]["responses"]["400"]
    assert response_400["content"] == {
        "application/json": {"schema": ref("OutOfStock")},
        "application/problem+json": {"schema": ref("Problem")},
    }


def test_merging_documents_any_of_and_keeps_runtime() -> None:
    with TestClient(load("options/merging").app) as client:
        invalid = client.post("/items", json={"name": "Hammer"})
        schema = client.get("/openapi.json").json()

    response_400 = schema["paths"]["/items"]["post"]["responses"]["400"]
    assert response_400["description"] == "Out of stock / Validation Error"
    assert response_400["content"]["application/json"]["schema"] == {
        "anyOf": [ref("HTTPValidationError"), ref("OutOfStock")]
    }
    assert invalid.status_code == 400
    assert set(invalid.json()) == {"detail"}


def test_merging_disabled_leaves_the_declared_response() -> None:
    with TestClient(load("options/merging_disabled").app) as client:
        schema = client.get("/openapi.json").json()

    response_400 = schema["paths"]["/items"]["post"]["responses"]["400"]
    assert response_400["description"] == "Out of stock"
    assert response_400["content"]["application/json"]["schema"] == ref("OutOfStock")


def test_custom_422_stays_next_to_the_validation_error() -> None:
    with TestClient(load("options/custom_422").app) as client:
        invalid = client.post("/items", json={"name": "Hammer"})
        schema = client.get("/openapi.json").json()

    responses = schema["paths"]["/items"]["post"]["responses"]
    assert responses["422"]["content"]["application/json"]["schema"] == ref("OutOfStock")
    assert responses["400"]["content"]["application/json"]["schema"] == ref("HTTPValidationError")
    assert invalid.status_code == 400


def test_handle_exceptions_false_uses_your_handler_and_patches_the_schema() -> None:
    with TestClient(load("options/exception_handler").app) as client:
        invalid = client.post("/items", json={"name": "Hammer"})
        schema = client.get("/openapi.json").json()

    assert invalid.status_code == 400
    assert set(invalid.json()) == {"message", "errors"}
    assert schema["paths"]["/items"]["post"]["responses"]["400"]["content"]["application/json"]["schema"] == ref(
        "HTTPValidationError"
    )


def test_custom_openapi_keeps_its_info_and_gets_patched() -> None:
    module = load("options/custom_openapi")
    with TestClient(module.app) as client:
        schema = client.get("/openapi.json").json()

    assert schema["info"] == {
        "title": "Inventory API",
        "version": "2.1.0",
        "x-logo": {"url": "https://example.com/logo.png"},
    }
    assert set(schema["paths"]["/items"]["post"]["responses"]) == {"200", "400"}


def test_custom_openapi_assigned_after_the_call_is_not_patched() -> None:
    module = load("options/custom_openapi")
    module.app.openapi_schema = None
    module.app.openapi = module.custom_openapi

    with TestClient(module.app) as client:
        schema = client.get("/openapi.json").json()
        invalid = client.post("/items", json={"name": "Hammer"})

    assert set(schema["paths"]["/items"]["post"]["responses"]) == {"200", "422"}
    assert invalid.status_code == 400


def test_patch_422_responses_patches_only_the_schema_it_receives() -> None:
    module = load("options/patch_422_responses")
    with TestClient(module.app) as client:
        app_schema = client.get("/openapi.json").json()
        invalid = client.post("/items", json={"name": "Hammer"})

    assert set(module.public_schema["paths"]["/items"]["post"]["responses"]) == {"200", "400"}
    assert set(app_schema["paths"]["/items"]["post"]["responses"]) == {"200", "422"}
    assert invalid.status_code == 422


def test_webhooks_and_callbacks_document_400() -> None:
    with TestClient(load("options/webhooks_and_callbacks").app) as client:
        schema = client.get("/openapi.json").json()

    operation = schema["paths"]["/items"]["post"]
    assert set(operation["responses"]) == {"200", "400"}
    assert set(schema["webhooks"]["item-created"]["post"]["responses"]) == {"200", "400"}
    callback = operation["callbacks"]["item_updated"]["{$callback_url}/updated"]["post"]
    assert set(callback["responses"]) == {"200", "400"}


def test_sub_app_override_applies_to_the_mounted_app_only() -> None:
    with TestClient(load("options/sub_app").app) as client:
        v2_invalid = client.post("/v2/items", json={})
        invalid = client.post("/items", json={})
        v2_schema = client.get("/v2/openapi.json").json()
        schema = client.get("/openapi.json").json()
        v2_docs = client.get("/v2/docs")

    assert v2_invalid.status_code == 400
    assert invalid.status_code == 422
    assert set(v2_schema["paths"]["/items"]["post"]["responses"]) == {"200", "400"}
    assert set(schema["paths"]["/items"]["post"]["responses"]) == {"200", "422"}
    assert v2_docs.status_code == 200


def test_error_builder_with_your_own_handler_sends_its_header_and_documents_the_model() -> None:
    with TestClient(load("options/error_builder_handler").app) as client:
        invalid = client.post("/items", json={"name": "Hammer"})
        schema = client.get("/openapi.json").json()

    assert invalid.status_code == 400
    assert invalid.headers["content-language"] == "en"
    assert invalid.json() == {
        "code": "VALIDATION_ERROR",
        "errors": [{"field": "body.price", "message": "Field required"}],
    }
    assert schema["paths"]["/items"]["post"]["responses"]["400"]["content"] == {
        "application/json": {"schema": ref("ErrorEnvelope")}
    }


def test_error_builder_reading_the_request_fills_instance() -> None:
    with TestClient(load("options/error_builder_request").app) as client:
        invalid = client.post("/items", json={"name": "Hammer"})
        schema = client.get("/openapi.json").json()

    assert invalid.status_code == 400
    assert invalid.headers["content-type"] == "application/problem+json"
    assert invalid.json() == {
        "type": "about:blank",
        "title": "Validation failed",
        "status": 400,
        "detail": "1 invalid field(s)",
        "instance": "/items",
    }
    assert schema["paths"]["/items"]["post"]["responses"]["400"]["content"] == {
        "application/problem+json": {"schema": ref("Problem")}
    }


def test_error_builder_keeping_fastapi_names_replaces_their_definitions() -> None:
    with TestClient(load("options/error_builder_fastapi_names").app) as client:
        invalid = client.post("/items", json={"name": "Hammer"})
        schema = client.get("/openapi.json").json()

    assert invalid.status_code == 400
    assert invalid.json() == {"detail": [{"field": "body.price", "message": "Field required"}]}
    components = schema["components"]["schemas"]
    assert set(components["HTTPValidationError"]["properties"]) == {"detail"}
    assert components["HTTPValidationError"]["properties"]["detail"]["items"] == ref("ValidationError")
    assert set(components["ValidationError"]["properties"]) == {"field", "message"}
    assert schema["paths"]["/items"]["post"]["responses"]["400"]["content"] == {
        "application/json": {"schema": ref("HTTPValidationError")}
    }
