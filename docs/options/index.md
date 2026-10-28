---
description: Every option of override_validation_error, one page each.
---

# Options

- [Error builder](error-builder.md): replace the body of the validation error with your own Pydantic model, in the response and in the schema.
- [Media type](media-type.md): send and document the error under another content type, such as `application/problem+json`.
- [Merge target response](merge-target-response.md): what happens when a route already declares a response at the target code.
- [Custom 422 response](custom-422-response.md): keep a `422` of your own next to the validation error.
- [Handle exceptions](handle-exceptions.md): patch the schema only, and send the response from your own handler.
- [Custom `app.openapi`](custom-openapi.md): keep a custom OpenAPI function you already have.
- [Patch 422 responses](patch-422-responses.md): patch a schema you build yourself with `get_openapi()`.
- [Webhooks and callbacks](webhooks-and-callbacks.md): the validation error in webhooks and callbacks.
- [Reverse proxy and sub-apps](reverse-proxy-and-sub-apps.md): `root_path`, and an override that applies to one mounted app only.
