from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from fastapi_validation_override import override_validation_error

app = FastAPI()


# --8<-- [start:snippet]
class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str


def build_problem(_request: Request, exc: RequestValidationError) -> Problem:
    return Problem(
        title="Validation failed",
        status=400,
        detail=f"{len(exc.errors())} invalid field(s)",
    )


override_validation_error(
    app, error_builder=build_problem, media_type="application/problem+json"
)
# --8<-- [end:snippet]


class Item(BaseModel):
    name: str
    quantity: int


class OutOfStock(BaseModel):
    item_name: str
    available: int


# --8<-- [start:orders]
@app.post(
    "/orders",
    responses={400: {"model": OutOfStock, "description": "Out of stock"}},
)
def create_order(item: Item) -> Item:
    return item


# --8<-- [end:orders]
