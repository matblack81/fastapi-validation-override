from fastapi import FastAPI
from fastapi_validation_override import override_validation_error
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    name: str
    price: float


@app.post("/items")
def create_item(item: Item) -> Item:
    return item


override_validation_error(app)
