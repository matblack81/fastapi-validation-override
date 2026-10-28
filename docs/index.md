---
title: Replace FastAPI's 422 validation error
description: Replace FastAPI's 422 validation error with the status code, body and content type you choose, at runtime and in the OpenAPI schema.
---

<div class="hero-logo" markdown>
![FastAPI Validation Override logo](assets/images/logo.svg){ width=128 }
</div>

# FastAPI Validation Override { .hero }

<p class="hero-tagline">Replace FastAPI's 422 validation error with the status code, body and content type you choose, at runtime and in the OpenAPI schema.</p>

FastAPI answers every request that fails validation with `422 Unprocessable Entity`, and documents that `422` on every route that validates input. Changing it takes two separate pieces: an exception handler for the response, and a patch of the OpenAPI schema for the docs. `override_validation_error` does both in one call, so the status code your API returns is the one its docs show.

```python
--8<-- "docs_src/quickstart/basic.py"
```

A `POST /items` with an invalid body now gets `400 Bad Request`, with the same `{"detail": [...]}` body FastAPI sends, and the OpenAPI schema documents the validation error at `400` instead of `422`. The [quick start](quickstart.md) shows the response and the schema in detail.

## What you can change

| Parameter | Default | What it changes |
|---|---|---|
| `status_code` | `400` | The status code of the validation error, in the response and in the schema |
| `error_builder` | `None` | The body of the error, built from your own Pydantic model, which the schema documents too |
| `media_type` | `"application/json"` | The content type of the error, e.g. `application/problem+json` for RFC 9457 Problem Details |
| `merge_target_response` | `True` | Whether a response the route already declares at the same code is merged with the validation error |
| `handle_exceptions` | `True` | Whether the response comes from the built-in handler or from yours |

The schema is patched across paths, webhooks and callbacks, on top of any custom `app.openapi` function you already have.

## Requirements

- Python 3.10+
- FastAPI 0.120.0+

## Installation

=== "pip"

    ```bash
    pip install fastapi-validation-override
    ```

=== "uv"

    ```bash
    uv add fastapi-validation-override
    ```
