---
description: An app behind a reverse proxy, and an override that applies to one mounted app only.
---

# Reverse proxy and sub-apps

## Behind a reverse proxy

Behind a proxy that serves the app under a path prefix, set the prefix on the server, for example with `fastapi run --root-path /api/v1`. The schema at `/api/v1/openapi.json` lists `/api/v1` in `servers`, and keeps the validation error at the target code.

## One override per app

`override_validation_error` applies to one FastAPI app. To use it on part of an API only, mount that part as its own app:

```python
--8<-- "docs_src/options/sub_app.py:snippet"
```

| Request that fails validation | Status code | Documented at |
|---|---|---|
| `POST /v2/items` | `400` | `/v2/openapi.json` |
| `POST /items` | `422` | `/openapi.json` |

Each app keeps its own docs: `/v2/docs` for the mounted one, `/docs` for the other.
