---
description: The validation error in webhooks and callbacks.
---

# Webhooks and callbacks

The validation error is moved in webhooks and callbacks too, the same way as in paths:

```python
--8<-- "docs_src/options/webhooks_and_callbacks.py:snippet"
```

| Operation | Documented codes |
|---|---|
| `POST /items` | `200`, `400` |
| Webhook `item-created` | `200`, `400` |
| Callback `{$callback_url}/updated` | `200`, `400` |

Without the override, the three would document `422`.
