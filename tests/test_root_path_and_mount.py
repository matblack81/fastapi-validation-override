from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from fastapi_validation_override import override_validation_error


class Item(BaseModel):  # pragma: no cover
    name: str


def test_root_path_set_by_the_server_keeps_the_schema_patched() -> None:
    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item) -> None: ...

    override_validation_error(app)

    with TestClient(app, root_path="/api/v1") as client:
        first = client.get("/api/v1/openapi.json").json()
        second = client.get("/api/v1/openapi.json").json()
        response = client.post("/api/v1/items", json={})

    assert first["servers"] == [{"url": "/api/v1"}]
    assert set(first["paths"]["/items"]["post"]["responses"]) == {"200", "400"}
    assert second == first
    assert response.status_code == 400


def test_mounted_app_is_patched_on_its_own() -> None:
    v2 = FastAPI()

    @v2.post("/items")
    async def create_item_v2(item: Item) -> None: ...

    override_validation_error(v2)

    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item) -> None: ...

    app.mount("/v2", v2)

    with TestClient(app, root_path="/api") as client:
        v2_schema = client.get("/api/v2/openapi.json").json()
        v2_response = client.post("/api/v2/items", json={})
        schema = client.get("/api/openapi.json").json()
        response = client.post("/api/items", json={})

    assert v2_schema["servers"] == [{"url": "/api/v2"}]
    assert set(v2_schema["paths"]["/items"]["post"]["responses"]) == {"200", "400"}
    assert v2_response.status_code == 400
    assert set(schema["paths"]["/items"]["post"]["responses"]) == {"200", "422"}
    assert response.status_code == 422


def test_route_added_after_the_schema_is_generated() -> None:
    """Recent FastAPI versions regenerate the schema for a route added later, older ones keep the
    cached one: either way, no operation in it documents 422, and the route returns 400 at runtime."""
    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item) -> None: ...

    override_validation_error(app)
    app.openapi()

    @app.post("/late")
    async def create_late(item: Item) -> None: ...

    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
        response = client.post("/late", json={})

    for path_item in schema["paths"].values():
        assert set(path_item["post"]["responses"]) == {"200", "400"}
    assert response.status_code == 400
