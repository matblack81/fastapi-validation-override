---
description: Keep a custom app.openapi function you already have.
---

# Custom `app.openapi`

`override_validation_error` wraps the `app.openapi` function the app has when you call it, and patches the schema that function returns. Assign your own function first:

```python
--8<-- "docs_src/options/custom_openapi.py:snippet"
```

The schema keeps your title, version and `x-logo`, and documents the validation error at `400`. The caching in your function keeps working: the patch is applied to the schema it returns.

Assigned after the call, your function replaces the wrapper and the schema is no longer patched, while the response still uses the new status code.
