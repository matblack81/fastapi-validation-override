---
description: Patch a schema you build yourself with get_openapi().
---

# Patch 422 responses

`patch_422_responses` is the schema patch on its own, for a schema you build with `fastapi.openapi.utils.get_openapi()` outside `app.openapi`:

```python
--8<-- "docs_src/options/patch_422_responses.py:snippet"
```

`public_schema` documents the validation error of `POST /items` at `400`, without the `422`. The function changes the schema it receives, and returns it too. The app itself is untouched: its `/openapi.json` still documents `422`, and a request that fails validation still gets `422`, unless you also call [`override_validation_error`](../quickstart.md).

It takes `merge_target_response`, with the same meaning as in [`override_validation_error`](merge-target-response.md). It's meant for the schemas `get_openapi()` produces; on documents written by hand or by other tools, the result is best effort.
