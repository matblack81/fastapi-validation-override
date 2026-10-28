---
description: Patch the schema only, and send the response from your own exception handler.
---

# Handle exceptions

With `handle_exceptions=False`, `override_validation_error` doesn't register an exception handler and only patches the schema. The response comes from your own handler:

```python
--8<-- "docs_src/options/exception_handler.py:snippet"
```

A request that fails validation gets your handler's response, here `400` with `{"message": "Validation failed", "errors": [...]}`, and the schema documents the validation error at `400`.

The schema still documents FastAPI's `HTTPValidationError` body, `{"detail": [...]}`, which this handler doesn't send. To change the body and its schema together, use an [error builder](error-builder.md) instead, which can't be combined with `handle_exceptions=False`.

Your handler also has to use the same status code and, if you set one, the same [`media_type`](media-type.md): the library doesn't check them.
