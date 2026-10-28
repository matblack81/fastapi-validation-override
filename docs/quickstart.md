---
description: Replace FastAPI's 422 validation error with 400, or any other status code, with one call.
---

# Quick start

Call `override_validation_error` with your app:

```python
--8<-- "docs_src/quickstart/basic.py"
```

A request whose body fails validation, such as `POST /items` with `{"name": "Hammer"}`, now gets `400 Bad Request`. The body is the one FastAPI sends for a `422`, unchanged:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "price"],
      "msg": "Field required",
      "input": {"name": "Hammer"}
    }
  ]
}
```

In the OpenAPI schema, `POST /items` documents `200` and `400`, and no longer `422`. The `400` response refers to the same `HTTPValidationError` component FastAPI uses for its `422`, so Swagger UI and ReDoc at `/docs` and `/redoc` show the same error, under the new code.

## Another status code

`status_code` takes any code that carries a response body:

```python
--8<-- "docs_src/quickstart/status_code.py:snippet"
```

The validation error is then sent and documented at `409`. Codes from 100 to 599 are accepted, except the ones that can't carry a body: 1xx, `204` and `304` raise `ValueError`. A `bool` or a value that isn't an `int` raises `TypeError`; `http.HTTPStatus` members work, since they are `int`s.

## Where to call it

Call it once, when you build the app. Routes added after the call are covered too: the exception handler applies to the whole app, and the schema is patched every time FastAPI generates it. A second call on the same app is ignored, even with different arguments.

## Next

The [options](options/index.md) change the body, its content type, and how the validation error combines with responses your routes already declare.
