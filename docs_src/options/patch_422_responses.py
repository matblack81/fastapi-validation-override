from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

from fastapi_validation_override import patch_422_responses

app = FastAPI()


class Item(BaseModel):
    name: str
    price: float


@app.post("/items")
def create_item(item: Item) -> Item:
    return item


# --8<-- [start:snippet]
public_schema = get_openapi(
    title="Inventory API", version="2.1.0", routes=app.routes
)
patch_422_responses(public_schema, "400")
# --8<-- [end:snippet]
