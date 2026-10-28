---
title: Replace FastAPI's 422 validation error
description: Replace FastAPI's 422 validation error with the status code, body and content type you choose, at runtime and in the OpenAPI schema.
---

<div class="hero-logo" markdown>
![FastAPI Validation Override logo](assets/images/logo.svg){ width=128 }
</div>

# FastAPI Validation Override { .hero }

<p class="hero-tagline">Replace FastAPI's 422 validation error with the status code, body and content type you choose, at runtime and in the OpenAPI schema.</p>

FastAPI answers every request that fails validation with `422 Unprocessable Entity`, and documents that `422` on every route that validates input. `override_validation_error` replaces it with the status code you choose, in the response and in the OpenAPI schema, with one call.

## Installation

```bash
pip install fastapi-validation-override
```
