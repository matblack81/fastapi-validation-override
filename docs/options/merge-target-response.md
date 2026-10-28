---
description: What happens when a route already declares a response at the target code.
---

# Merge target response

When a route already declares a response at the target code, the validation error is merged into it with `anyOf` instead of replacing it:

```python
--8<-- "docs_src/options/merging.py:snippet"
```

The `400` of `POST /items` documents `anyOf: [HTTPValidationError, OutOfStock]`, and its description becomes `Out of stock / Validation Error`. At runtime nothing changes: a request that fails validation gets the validation error, and `OutOfStock` is for errors you raise yourself.

The merge happens within one content type. With a [`media_type`](media-type.md) other than `application/json`, a response declared under `application/json` is kept next to the validation error instead.

## Leave the response untouched

With `merge_target_response=False`, a response the route declares at the target code is left as it is:

```python
--8<-- "docs_src/options/merging_disabled.py:snippet"
```

The `400` of `POST /items` then documents only `OutOfStock`, described as `Out of stock`. Routes that don't declare a `400` still get the validation error.

A response declared as a `$ref` at the target code is always left untouched, whatever `merge_target_response` says.
