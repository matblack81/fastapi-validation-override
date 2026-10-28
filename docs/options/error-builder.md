---
description: Replace the body of the validation error with your own Pydantic model, in the response and in the schema.
---

# Error builder

`error_builder` takes a function that builds the response body from the request and the `RequestValidationError`, like FastAPI's exception handlers. Its return annotation is the model the schema documents, so the body and the schema can't drift apart:

```python
--8<-- "docs_src/options/error_builder.py:snippet"
```

A `POST /items` with `{"name": "Hammer"}` now gets `400` with:

```json
{
  "code": "VALIDATION_ERROR",
  "errors": [{"field": "body.price", "message": "Field required"}]
}
```

In the schema, the `400` of `POST /items` refers to `ErrorEnvelope`, and `ErrorEnvelope` and `FieldError` are added to `components.schemas`. FastAPI's own `HTTPValidationError` and `ValidationError` components are removed, since nothing refers to them anymore. `GET /health` has no body or parameters, so it can't fail validation and gets no `400`.

The function can be regular or `async`. If it can't be called with the request and the exception, or its return annotation isn't a Pydantic model, `override_validation_error` raises `TypeError`.

## Names already in the schema

- A component with the same name and the same definition is reused: a route that also returns `ErrorEnvelope` and the validation error share one component.
- A different component already registered under the same name is left as it is, and your model and the ones it nests are added under `FastAPIValidationOverride_`-prefixed names.
- Models named `HTTPValidationError` and `ValidationError` take the place of FastAPI's components, under the same names.

!!! warning "A response model named `HTTPValidationError` documents FastAPI's definition"

    FastAPI adds its own components under the names `HTTPValidationError` and `ValidationError` after the models of the routes, so a route whose response model has one of those names documents FastAPI's definition instead of yours, with or without this library. Since that route still refers to FastAPI's component, it isn't removed, and the validation error is documented under the `FastAPIValidationOverride_` names. Give the model another name if a route returns it too.

## Reading the request

The request is there for a body that depends on it. Here the function fills the `instance` member of [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) Problem Details with the path of the request:

```python
--8<-- "docs_src/options/error_builder_request.py:snippet"
```

A `POST /items` that fails validation gets:

```json
{
  "type": "about:blank",
  "title": "Validation failed",
  "status": 400,
  "detail": "1 invalid field(s)",
  "instance": "/items"
}
```

## With your own exception handler

With `handle_exceptions=False`, the library doesn't call the function: it only reads the model the schema documents. Your own handler calls it, and can add headers, log, or read the request:

```python
--8<-- "docs_src/options/error_builder_handler.py:snippet"
```

A request that fails validation gets the `ErrorEnvelope` body with a `Content-Language: en` header, and the schema documents `ErrorEnvelope` at `400`. The status code and the content type your handler sends have to match `status_code` and [`media_type`](media-type.md): the library doesn't check them.

## With `status_code=422`

`status_code=422` together with `error_builder` keeps FastAPI's status code and replaces only the body and its schema.

To send the body under another content type, such as `application/problem+json`, combine it with [`media_type`](media-type.md).
