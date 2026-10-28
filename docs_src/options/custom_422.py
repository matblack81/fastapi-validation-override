from fastapi import FastAPI
from fastapi_validation_override import override_validation_error
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    name: str
    price: float


# --8<-- [start:snippet]
class OutOfStock(BaseModel):
    item_name: str


@app.post(
    "/items",
    responses={
        422: {"model": OutOfStock, "description": "Item is out of stock"}
    },
)
def create_item(item: Item) -> Item:
    return item


override_validation_error(app)
# --8<-- [end:snippet]
