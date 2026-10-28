from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

from fastapi_validation_override import override_validation_error

app = FastAPI()


class Item(BaseModel):
    name: str
    price: float


class ItemUpdate(BaseModel):
    status: str


# --8<-- [start:snippet]
@app.webhooks.post("item-created")
def item_created(item: Item) -> None:
    """Sent to subscribers when an item is created."""


callback_router = APIRouter()


@callback_router.post("{$callback_url}/updated")
def item_updated(update: ItemUpdate) -> None: ...


@app.post("/items", callbacks=callback_router.routes)
def create_item(item: Item) -> Item:
    return item


override_validation_error(app)
# --8<-- [end:snippet]
