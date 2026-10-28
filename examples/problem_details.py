"""
Return validation errors as RFC 9457 Problem Details, with the application/problem+json content type.

The 400 of POST /orders documents two errors under two content types: OutOfStock under
application/json, declared by the route, and the validation error under application/problem+json.

Run:

    uvicorn examples.problem_details:app --reload
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from fastapi_validation_override import override_validation_error

app = FastAPI(
    title="Problem Details Example",
    description="Validation errors are returned and documented as application/problem+json.",
)


class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str


def build_problem(_request: Request, exc: RequestValidationError) -> Problem:
    return Problem(title="Validation failed", status=400, detail=f"{len(exc.errors())} invalid field(s)")


class OutOfStock(BaseModel):
    item_name: str
    available: int


class Item(BaseModel):
    name: str
    quantity: int


@app.post("/items")
async def create_item(item: Item) -> dict[str, Any]:
    return item.model_dump()


@app.post("/orders", responses={400: {"model": OutOfStock, "description": "Out of stock"}})
async def create_order(item: Item) -> dict[str, Any]:
    return item.model_dump()


override_validation_error(app, error_builder=build_problem, media_type="application/problem+json")
