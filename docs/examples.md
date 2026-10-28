---
description: Twelve runnable apps, one per use of override_validation_error.
---

# Examples

Every example is a complete, runnable app, imported and checked by the test suite. Run one with `uvicorn examples.<name>:app --reload` from a checkout of the repository, then open `http://127.0.0.1:8000/docs`.

## `basic.py`

The default setup: the validation error at `400`.

??? example "Show the code"

    ```python
    --8<-- "examples/basic.py"
    ```

## `custom_status_code.py`

The validation error at `409`.

??? example "Show the code"

    ```python
    --8<-- "examples/custom_status_code.py"
    ```

## `error_builder.py`

The error body and its schema from a Pydantic model, with `error_builder`.

??? example "Show the code"

    ```python
    --8<-- "examples/error_builder.py"
    ```

## `error_builder_fastapi_names.py`

An error builder whose models keep FastAPI's names, `HTTPValidationError` and `ValidationError`, with a body of your own shape.

??? example "Show the code"

    ```python
    --8<-- "examples/error_builder_fastapi_names.py"
    ```

## `problem_details.py`

RFC 9457 Problem Details as `application/problem+json`, next to an `application/json` error at the same code.

??? example "Show the code"

    ```python
    --8<-- "examples/problem_details.py"
    ```

## `existing_response_at_target_code.py`

The validation error merged with `anyOf` into a response the route already declares at `400`.

??? example "Show the code"

    ```python
    --8<-- "examples/existing_response_at_target_code.py"
    ```

## `custom_422_response.py`

A route's own `422` kept next to the validation error at `400`.

??? example "Show the code"

    ```python
    --8<-- "examples/custom_422_response.py"
    ```

## `handle_exceptions_false.py`

Your own exception handler, with only the schema patched.

??? example "Show the code"

    ```python
    --8<-- "examples/handle_exceptions_false.py"
    ```

## `custom_validation_schema.py`

FastAPI's own validation error definitions reassigned to a custom error envelope, with a handler that sends it.

??? example "Show the code"

    ```python
    --8<-- "examples/custom_validation_schema.py"
    ```

## `custom_openapi.py`

A custom `app.openapi` function, kept and patched.

??? example "Show the code"

    ```python
    --8<-- "examples/custom_openapi.py"
    ```

## `with_apirouter.py`

Routes split across several `APIRouter`s.

??? example "Show the code"

    ```python
    --8<-- "examples/with_apirouter.py"
    ```

## `webhooks_and_callbacks.py`

The validation error in webhooks and callbacks.

??? example "Show the code"

    ```python
    --8<-- "examples/webhooks_and_callbacks.py"
    ```
