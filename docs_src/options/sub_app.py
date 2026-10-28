from fastapi import FastAPI
from fastapi_validation_override import override_validation_error
from pydantic import BaseModel


class Item(BaseModel):
    name: str
    price: float


# --8<-- [start:snippet]
v2 = FastAPI()


@v2.post("/items")
def create_item_v2(item: Item) -> Item:
    return item


override_validation_error(v2)

app = FastAPI()


@app.post("/items")
def create_item(item: Item) -> Item:
    return item


app.mount("/v2", v2)
# --8<-- [end:snippet]
