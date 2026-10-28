---
description: Send and document the validation error under another content type, such as application/problem+json.
---

# Media type

`media_type` sets the content type of the validation error, both in the response header and in the schema. Combined with an [error builder](error-builder.md), it returns [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) Problem Details:

```python
--8<-- "docs_src/options/media_type.py:snippet"
```

A request that fails validation gets `400` with `content-type: application/problem+json`:

```json
{
  "type": "about:blank",
  "title": "Validation failed",
  "status": 400,
  "detail": "1 invalid field(s)"
}
```

and the schema documents the `400` under the `application/problem+json` key.

`media_type` must be `application/json` or a content type ending in `+json`, since the body is always JSON; anything else raises `ValueError`. It also works without `error_builder`, with the default `{"detail": [...]}` body.

## Another error at the same code

A response the route already declares at the target code under another content type is kept next to the validation error, not merged with it:

```python
--8<-- "docs_src/options/media_type.py:orders"
```

| Content type | Model |
|---|---|
| `application/json` | `OutOfStock` |
| `application/problem+json` | `Problem` |

Swagger UI and ReDoc show the two under the media type menu of the `400` response. Under the same content type, the two models are [merged with `anyOf`](merge-target-response.md) instead.

## With `handle_exceptions=False`

Only the schema uses `media_type`: your own handler has to send the same content type.

## With `status_code=422`

`status_code=422` with a `media_type` other than `application/json` is not a no-op: it keeps the `422` and changes its content type.
