---
description: Keep a 422 response of your own next to the validation error.
---

# Custom 422 response

Only the `422` that FastAPI generates for validation is removed. A `422` the route declares itself stays, and the validation error is documented at the target code anyway:

```python
--8<-- "docs_src/options/custom_422.py:snippet"
```

`POST /items` documents `422` with `OutOfStock` and `400` with `HTTPValidationError`.

A request that fails validation still gets `400`: `responses={422: ...}` only changes the docs, not which handler FastAPI calls. The `422` is for errors you raise yourself.

!!! note "A hidden parameter with its own `422` isn't detected"

    A parameter declared with `include_in_schema=False` is validated, but doesn't appear in the schema. If its route also declares a response at `422`, `4XX` or `default`, FastAPI doesn't add its own `422` either, and nothing in the schema shows that the route validates input. The target code isn't documented for that route, although the route can return it.
