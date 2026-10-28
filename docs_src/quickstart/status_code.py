from fastapi import FastAPI
from pydantic import BaseModel

from fastapi_validation_override import override_validation_error

app = FastAPI()


class Item(BaseModel):
    name: str
    price: float


@app.post("/items")
def create_item(item: Item) -> Item:
    return item


# --8<-- [start:snippet]
override_validation_error(app, status_code=409)
# --8<-- [end:snippet]
