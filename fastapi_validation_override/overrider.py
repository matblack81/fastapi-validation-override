import inspect

from collections.abc import Callable, Iterator
from copy import deepcopy
from functools import partial
from typing import Any, get_type_hints

import fastapi.openapi.utils as fastapi_openapi_utils

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.constants import REF_PREFIX
from fastapi.responses import JSONResponse

_HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
_VALIDATION_ERROR_REF = {"$ref": f"{REF_PREFIX}HTTPValidationError"}


def _validation_error_ref(name: str = "HTTPValidationError") -> dict[str, str]:
    """Fresh dict: never share the same object across routes or apps."""
    return {"$ref": f"{REF_PREFIX}{name}"}


def _operation_needs_validation(operation: dict[str, Any]) -> bool:
    return bool(operation.get("requestBody")) or bool(operation.get("parameters"))


def _iter_path_item_operations(path_item: dict[str, Any]) -> Iterator[dict[str, Any]]:
    for method, operation in path_item.items():
        if method not in _HTTP_METHODS or not isinstance(operation, dict):
            # path_item may hold non-operation keys (summary, parameters, ...) or itself be a $ref
            continue
        yield operation


def _iter_operations(schema: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """
    Yield every Operation Object in the schema: paths, webhooks, and callbacks, recursively.
    A callback declared as a `$ref` instead of an inline Path Item mapping is silently skipped:
    `get_openapi()` never produces one, and this module doesn't resolve `$ref`s.
    """
    for container_key in ("paths", "webhooks"):
        container = schema.get(container_key)
        if not isinstance(container, dict):
            continue

        for path_item in container.values():
            if not isinstance(path_item, dict):
                continue

            for operation in _iter_path_item_operations(path_item):
                yield operation

                callbacks = operation.get("callbacks")
                if isinstance(callbacks, dict):
                    for callback_paths in callbacks.values():
                        if isinstance(callback_paths, dict):
                            yield from _iter_operations({"paths": callback_paths})


def _replace_ref(value: Any, old_ref: str, new_ref: str) -> None:
    """Recursively rewrite every $ref matching old_ref to new_ref, regardless of the envelope shape."""
    if isinstance(value, dict):
        if value.get("$ref") == old_ref:
            value["$ref"] = new_ref
        for child in value.values():
            _replace_ref(child, old_ref, new_ref)
    elif isinstance(value, list):
        for child in value:
            _replace_ref(child, old_ref, new_ref)


def _references(value: Any, ref: str) -> bool:
    if isinstance(value, dict):
        return value.get("$ref") == ref or any(_references(child, ref) for child in value.values())
    if isinstance(value, list):
        return any(_references(child, ref) for child in value)
    return False


def _resolve_validation_ref(schema: dict[str, Any]) -> str:
    """
    Ensure ValidationError/HTTPValidationError components exist in `schema`, picking an alternate
    name for either one the schema already declares for something else. Returns the name the
    HTTPValidationError component is registered under — inserted by this call if absent, or an
    already-matching component left untouched.
    """
    components = schema.setdefault("components", {}).setdefault("schemas", {})

    validation_error_definition = fastapi_openapi_utils.validation_error_definition
    validation_error_response_definition = fastapi_openapi_utils.validation_error_response_definition

    validation_error_name = "ValidationError"
    existing_ve = components.get(validation_error_name)
    if existing_ve is not None and existing_ve != validation_error_definition:
        validation_error_name = "FastAPIValidationOverride_ValidationError"

    http_validation_error_def: dict[str, Any] = deepcopy(validation_error_response_definition)
    if validation_error_name != "ValidationError":
        _replace_ref(http_validation_error_def, f"{REF_PREFIX}ValidationError", f"{REF_PREFIX}{validation_error_name}")

    http_validation_error_name = "HTTPValidationError"
    existing_http_validation_error = components.get(http_validation_error_name)
    if existing_http_validation_error is not None and existing_http_validation_error != http_validation_error_def:
        http_validation_error_name = "FastAPIValidationOverride_HTTPValidationError"

    if validation_error_name not in components:
        components[validation_error_name] = deepcopy(validation_error_definition)
    if http_validation_error_name not in components:
        components[http_validation_error_name] = http_validation_error_def

    return http_validation_error_name


def _resolve_model_ref(schema: dict[str, Any], model: Any) -> str:
    """
    Insert `model` and the models it nests into `schema`'s components, reusing any identical
    component already there. If a name is taken by a different definition, all of them go under
    namespaced names, so the $refs between them stay consistent. Returns the model's component name.
    """
    components = schema.setdefault("components", {}).setdefault("schemas", {})

    name: str = model.__name__
    model_schema = model.model_json_schema(mode="serialization", ref_template=f"{REF_PREFIX}{{model}}")
    definitions: dict[str, Any] = model_schema.pop("$defs", {})
    # A self-referencing model is already in $defs, and its top level is only a $ref to it
    definitions.setdefault(name, model_schema)

    if any(components.get(def_name, definition) != definition for def_name, definition in definitions.items()):
        for def_name in list(definitions):
            _replace_ref(definitions, f"{REF_PREFIX}{def_name}", f"{REF_PREFIX}FastAPIValidationOverride_{def_name}")
        definitions = {f"FastAPIValidationOverride_{def_name}": d for def_name, d in definitions.items()}
        name = f"FastAPIValidationOverride_{name}"

    for def_name, definition in definitions.items():
        components.setdefault(def_name, definition)

    return name


def _drop_unreferenced_validation_components(schema: dict[str, Any]) -> None:
    """FastAPI declares these for every app that validates, whether or not anything still points at them."""
    components = schema.get("components", {}).get("schemas", {})
    for name, definition in (
        ("HTTPValidationError", fastapi_openapi_utils.validation_error_response_definition),
        ("ValidationError", fastapi_openapi_utils.validation_error_definition),
    ):
        if components.get(name) == definition and not _references(schema, f"{REF_PREFIX}{name}"):
            del components[name]


def patch_422_responses(
    schema: dict[str, Any], target_code: str, *, merge_target_response: bool = True
) -> dict[str, Any]:
    """
    Move FastAPI's 422 validation error response to `target_code`, across paths, webhooks, and
    callbacks (recursively, for callbacks declared on any operation).

    Designed for schemas produced by `fastapi.openapi.utils.get_openapi()` — the same generator
    `app.openapi()` uses internally. It's exposed publicly so it can be patched outside
    `override_validation_error`, e.g. from a custom `app.openapi` function or a tool that builds its
    own per-version schema via `get_openapi()`. It is not meant as a general-purpose processor for
    arbitrary or hand-authored OpenAPI documents: correctness on documents built by hand or by other
    tools is best-effort, not a guarantee.

    A parameter declared with `include_in_schema=False` still triggers validation at runtime, but
    is invisible in the generated schema. If such a route also already occupies 422, `4XX`, or
    `default` with something else, FastAPI never emits its own 422 response for that operation —
    the only signal this function relies on to detect the need for validation on such a parameter.
    In that specific combination, `target_code` won't be documented.

    :param schema: An OpenAPI schema dict produced by `fastapi.openapi.utils.get_openapi()`, such as
        one returned by `app.openapi()`.
    :param target_code: The status code to document the validation error at, e.g. `"400"`.
    :param merge_target_response: If True (default), a response already declared at `target_code`
        is merged with the validation error schema using `anyOf`. If False, it is left untouched.
        A response declared as a `$ref` is always left untouched regardless of this flag:
        `get_openapi()` never produces one at a route's own declared status code, and this module
        doesn't resolve `$ref`s.
    :return: The same `schema` dict, mutated in place.
    """
    operations = _remove_fastapi_422_responses(schema)
    _document_validation_responses(schema, operations, target_code, merge_target_response, _resolve_validation_ref)
    return schema


def _remove_fastapi_422_responses(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Returns the operations that validate input, the ones whose FastAPI 422 response was removed included."""
    operations = []

    for operation in _iter_operations(schema):
        responses = operation.setdefault("responses", {})

        removed_fastapi_422 = False
        response_422 = responses.get("422")
        if response_422 is not None:
            schema_422 = response_422.get("content", {}).get("application/json", {}).get("schema", {})
            if schema_422 == _VALIDATION_ERROR_REF:
                del responses["422"]
                removed_fastapi_422 = True

        if removed_fastapi_422 or _operation_needs_validation(operation):
            operations.append(operation)

    return operations


def _document_validation_responses(
    schema: dict[str, Any],
    operations: list[dict[str, Any]],
    target_code: str,
    merge_target_response: bool,
    resolve_component: Callable[[dict[str, Any]], str],
    media_type: str = "application/json",
) -> None:
    """`resolve_component` registers the error body's component in `schema` and returns its name."""
    component_name: str | None = None

    for operation in operations:
        responses = operation["responses"]

        if target_code in responses:
            if not merge_target_response:
                continue

            existing_response = responses[target_code]
            if "$ref" in existing_response:
                continue

            if component_name is None:
                component_name = resolve_component(schema)
            validation_ref = _validation_error_ref(component_name)

            existing_content = existing_response.setdefault("content", {}).setdefault(media_type, {})
            existing_schema = existing_content.setdefault("schema", {})

            if "anyOf" in existing_schema:
                if validation_ref not in existing_schema["anyOf"]:
                    existing_schema["anyOf"].insert(0, _validation_error_ref(component_name))
            elif existing_schema and existing_schema != validation_ref:
                existing_content["schema"] = {"anyOf": [_validation_error_ref(component_name), existing_schema]}
            elif not existing_schema:
                existing_content["schema"] = _validation_error_ref(component_name)

            old_desc = existing_response.get("description", "Error")
            if "Validation Error" not in old_desc:
                existing_response["description"] = f"{old_desc} / Validation Error"
        else:
            if component_name is None:
                component_name = resolve_component(schema)

            responses[target_code] = {
                "description": "Validation Error",
                "content": {media_type: {"schema": _validation_error_ref(component_name)}},
            }


def override_validation_error(
    app: FastAPI,
    status_code: int = 400,
    handle_exceptions: bool = True,
    merge_target_response: bool = True,
    error_builder: Callable[[RequestValidationError], Any] | None = None,
    media_type: str = "application/json",
) -> None:
    """
    Override FastAPI's default 422 validation error response with a custom status code.

    Cache management is intentionally delegated to the original `app.openapi` so that
    any custom OpenAPI function already set by the developer is fully preserved.

    The first call configures the app. Subsequent calls on the same instance are ignored, even
    with different arguments. Dynamic reconfiguration is not supported.

    :param app: The FastAPI application instance to patch.
    :param status_code: The HTTP status code to use instead of 422. Defaults to 400. Passing 422
        without `error_builder` and with the default `media_type` is a no-op: the app is left
        completely unpatched, matching FastAPI's own default.
    :param handle_exceptions: If True, registers an exception handler that returns the custom
        status code at runtime. Set to False to patch only the OpenAPI schema and
        handle the exception yourself.
    :param merge_target_response: If True (default), a response you already declared at
        `status_code` is merged with the validation error schema using `anyOf`. If False,
        it is left untouched.
    :param error_builder: A regular (not async) function that turns the `RequestValidationError`
        into the response body, annotated with a Pydantic model as its return type. The handler
        returns what it builds, and the schema documents that model at `status_code` instead of
        `HTTPValidationError`, on the operations that validate input. FastAPI's
        `HTTPValidationError`/`ValidationError` components are then removed, unless something in
        the schema still references them.
    :param media_type: The content type of the validation error, e.g. `"application/problem+json"`.
        The handler sends it, and the schema documents the error under it. A response already
        declared at `status_code` under another content type is kept alongside, not merged with
        `anyOf`. With `handle_exceptions=False`, your own handler has to send it.
    :return: None. `app` is patched in place.
    :raises TypeError: If `status_code` is not an `int` (a `bool` is also rejected, since it's
        technically an `int` subclass in Python), or if `error_builder` is async or its return
        annotation is not a Pydantic model.
    :raises ValueError: If `status_code` is not a valid HTTP status code (100-599), or is one of
        the codes that must not carry a response body (1xx, 204, 304) — this library always
        returns one — or if `error_builder` is passed with `handle_exceptions=False`, or if
        `media_type` is not a JSON content type (`application/json` or one ending in `+json`).
    """
    if isinstance(status_code, bool) or not isinstance(status_code, int):
        raise TypeError(f"status_code must be an int, got {type(status_code).__name__}: {status_code!r}")
    status_code = int(status_code)
    if not (100 <= status_code <= 599):
        raise ValueError(f"status_code must be a valid HTTP status code (100-599), got {status_code}")
    if status_code < 200 or status_code in (204, 304):
        raise ValueError(
            f"status_code {status_code} does not support a response body, but this library always sends one"
        )
    if not (media_type == "application/json" or media_type.endswith("+json")):
        raise ValueError(f"media_type must be a JSON content type, since the body is JSON, got {media_type!r}")

    error_model: Any = None
    if error_builder is not None:
        if not handle_exceptions:
            raise ValueError("error_builder requires handle_exceptions=True: it builds the body that handler returns")
        if inspect.iscoroutinefunction(error_builder):
            raise TypeError("error_builder must be a regular function, not async")
        error_model = get_type_hints(error_builder).get("return")
        if not (isinstance(error_model, type) and hasattr(error_model, "model_json_schema")):
            raise TypeError(f"error_builder must declare a Pydantic model as its return type, got {error_model!r}")

    if status_code == 422 and error_builder is None and media_type == "application/json":
        return

    if getattr(app.state, "_validation_overridden", False):
        return

    if handle_exceptions:

        @app.exception_handler(RequestValidationError)
        async def custom_validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
            body = error_builder(exc) if error_builder is not None else {"detail": exc.errors()}
            return JSONResponse(status_code=status_code, content=jsonable_encoder(body), media_type=media_type)

    target_code = str(status_code)
    original_openapi = app.openapi
    resolve_component = (
        _resolve_validation_ref if error_model is None else partial(_resolve_model_ref, model=error_model)
    )

    def custom_openapi() -> dict[str, Any]:
        schema = original_openapi()
        operations = _remove_fastapi_422_responses(schema)
        if error_model is not None:
            # Before the model is registered, so its names don't collide with components about to go
            _drop_unreferenced_validation_components(schema)
        _document_validation_responses(
            schema, operations, target_code, merge_target_response, resolve_component, media_type
        )
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]  # ty: ignore[invalid-assignment]
    app.state._validation_overridden = True
