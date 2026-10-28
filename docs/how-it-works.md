---
description: What override_validation_error does to the app and to its OpenAPI schema, step by step.
---

# How it works

`override_validation_error` is a setup step: you call it once, and it changes two things on the app, the handler of `RequestValidationError` and the `app.openapi` function. The steps below follow the order of the code.

## 1. Checking the arguments

Every argument is checked before anything is registered on the app:

- `status_code` must be an `int`, and not a `bool`, otherwise `TypeError`. It must be between 100 and 599 and able to carry a body, so not 1xx, `204` or `304`, otherwise `ValueError`. An `int` subclass such as `http.HTTPStatus` is turned into a plain `int`.
- `media_type` must be `application/json` or end in `+json`, otherwise `ValueError`.
- `error_builder`, when given, must be callable with the request and the exception, and have a Pydantic model as its return annotation, otherwise `TypeError`.

When a check fails, the app is left as it was.

## 2. When nothing changes

The call returns without changing the app in two cases:

- `status_code=422`, without `error_builder` and with the default `media_type`: that's what FastAPI already does.
- The app was already configured by a previous call, whatever the arguments of that call.

## 3. The exception handler

With `handle_exceptions=True`, a handler for `RequestValidationError` is registered on the app. It builds the body with `error_builder(request, exc)`, awaiting it if the function is `async`, or as `{"detail": exc.errors()}` without one, encodes it with `fastapi.encoders.jsonable_encoder`, and returns it with `status_code` and `media_type`.

With `handle_exceptions=False`, no handler is registered and `error_builder` is never called: the remaining steps only change the schema, which still documents the model of `error_builder`.

## 4. Wrapping `app.openapi`

`app.openapi` is replaced with a function that calls the one the app had before, patches the schema it returns, and stores it in `app.openapi_schema`. A custom `app.openapi` assigned before the call keeps running, with its caching. The patch runs every time the schema is generated, and the steps below are that patch.

## 5. Removing FastAPI's 422

Every operation is visited: the paths, the webhooks, and the callbacks declared inline on them. A `422` response whose `application/json` schema is exactly a reference to `HTTPValidationError` is the one FastAPI generates for validation, and is removed. Any other `422` stays.

An operation validates input, and gets the validation error at the target code, if its FastAPI `422` was removed, or if it has a request body or parameters.

## 6. FastAPI's components, with an error builder

With `error_builder`, FastAPI's `HTTPValidationError` and `ValidationError` components are removed, if they are still FastAPI's definitions and nothing in the schema refers to them anymore. This happens before your model is added, so a model with one of those names can take its place.

## 7. The response at the target code

For each operation that validates input:

- Without a response at the target code, one is added: described as `Validation Error`, with the error's component under the `media_type` key.
- With a response already there, it's left untouched if `merge_target_response=False` or if it's a `$ref`. Otherwise the error's component goes under the `media_type` key of that response: alone if the key had no schema, prepended to an existing `anyOf` that doesn't list it yet, or combined with the existing schema in a new `anyOf`. `Validation Error` is appended to its description.

## 8. The error's component

The component is added to `components.schemas` the first time an operation needs it, so a schema with no operation that validates input gets none.

- **Without an error builder**, it's FastAPI's `HTTPValidationError`, with the `ValidationError` it refers to. Both definitions are read from `fastapi.openapi.utils` when the schema is generated, so reassigning them before that changes what is documented. If the schema already has a different component under one of those names, a `FastAPIValidationOverride_`-prefixed name is used for it instead.
- **With an error builder**, it's the schema Pydantic generates for the model in serialization mode, with the models it nests. A component with the same name and definition is reused; if any of the names is taken by a different definition, all of them get the `FastAPIValidationOverride_` prefix, so the references between them stay consistent.
