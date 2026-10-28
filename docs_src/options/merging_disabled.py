from fastapi import FastAPI
from fastapi_validation_override import override_validation_error
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    name: str
    price: float


class OutOfStock(BaseModel):
    item_name: str


@app.post(
    "/items",
    responses={400: {"model": OutOfStock, "description": "Out of stock"}},
)
def create_item(item: Item) -> Item:
    return item


# --8<-- [start:snippet]
override_validation_error(app, merge_target_response=False)
# --8<-- [end:snippet]
