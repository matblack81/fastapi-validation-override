<p align="center">
  <img src="https://raw.githubusercontent.com/matblack81/fastapi-validation-override/main/docs/assets/images/logo.svg" alt="FastAPI Validation Override logo" width="128">
</p>

<h1 align="center">
  <img src="https://raw.githubusercontent.com/matblack81/fastapi-validation-override/main/docs/assets/images/wordmark.png" alt="FastAPI Validation Override" width="525">
</h1>

<p align="center">
  <a href="https://github.com/matblack81/fastapi-validation-override/actions"><img src="https://github.com/matblack81/fastapi-validation-override/workflows/Test/badge.svg" alt="Build Status"></a>
  <a href="https://codecov.io/github/matblack81/fastapi-validation-override"><img src="https://codecov.io/github/matblack81/fastapi-validation-override/graph/badge.svg?token=SL4JPWAB0O" alt="codecov"></a>
  <a href="https://pypi.org/project/fastapi-validation-override/"><img src="https://img.shields.io/pypi/v/fastapi-validation-override?color=%2334D058&label=pypi%20package" alt="pypi package"></a>
  <a href="https://pypi.org/project/fastapi-validation-override/"><img src="https://img.shields.io/pypi/pyversions/fastapi-validation-override.svg?color=%2334D058" alt="Supported Python versions"></a>
  <a href="https://github.com/matblack81/fastapi-validation-override/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT"></a>
</p>

FastAPI answers every request that fails validation with `422 Unprocessable Entity`, and documents that `422` on every route that validates input. Changing it takes two separate pieces: an exception handler for the response, and a patch of the OpenAPI schema for the docs. `override_validation_error` does both in one call, so the status code your API returns is the one its docs show.

Documentation: https://fastapi-validation-override.matblack81.com/

---

## What you can change

| Parameter | Default | What it changes |
|---|---|---|
| [`status_code`](https://fastapi-validation-override.matblack81.com/quickstart/#another-status-code) | `400` | The status code of the validation error, in the response and in the schema |
| [`error_builder`](https://fastapi-validation-override.matblack81.com/options/error-builder/) | `None` | The body of the error, built from your own Pydantic model, which the schema documents too |
| [`media_type`](https://fastapi-validation-override.matblack81.com/options/media-type/) | `"application/json"` | The content type of the error, e.g. `application/problem+json` for RFC 9457 Problem Details |
| [`merge_target_response`](https://fastapi-validation-override.matblack81.com/options/merge-target-response/) | `True` | Whether a response the route already declares at the same code is merged with the validation error |
| [`handle_exceptions`](https://fastapi-validation-override.matblack81.com/options/handle-exceptions/) | `True` | Whether the response comes from the built-in handler or from yours |

The schema is patched across paths, [webhooks and callbacks](https://fastapi-validation-override.matblack81.com/options/webhooks-and-callbacks/), on top of any [custom `app.openapi`](https://fastapi-validation-override.matblack81.com/options/custom-openapi/) function you already have.

---

## Requirements

- Python 3.10+
- FastAPI 0.120.0+

---

## Installation

```bash
pip install fastapi-validation-override
# or
uv add fastapi-validation-override
```

---

## Quick start

Call `override_validation_error` with your app:

```python
from fastapi import FastAPI
from pydantic import BaseModel

from fastapi_validation_override import override_validation_error

app = FastAPI()


class Item(BaseModel):
    name: str
    price: float


@app.post("/items")
def create_item(item: Item) -> Item:
    return item


override_validation_error(app)
```

The response, the schema, the other options and the parameter reference are in the [documentation](https://fastapi-validation-override.matblack81.com/).

---

## Release Notes

[RELEASE_NOTES](https://github.com/matblack81/fastapi-validation-override/blob/main/docs/release-notes.md)

---

## License

[MIT](https://github.com/matblack81/fastapi-validation-override/blob/main/LICENSE)
