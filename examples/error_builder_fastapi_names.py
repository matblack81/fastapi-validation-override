"""
Replace the validation error body with your own models, under FastAPI's component names.

Naming the models HTTPValidationError and ValidationError keeps the type names that clients
generated from the schema already use, while the body takes the shape you define. They take the
place of FastAPI's components. Don't also use them as a route's response model: FastAPI would
overwrite them with its own definitions.

Run:

    uvicorn examples.error_builder_fastapi_names:app --reload
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from fastapi_validation_override import override_validation_error

app = FastAPI(
    title="Error Builder with FastAPI's Names Example",
    description="Validation errors keep FastAPI's component names, with a body of your own shape.",
)


class ValidationError(BaseModel):
    field: str
    message: str


class HTTPValidationError(BaseModel):
    detail: list[ValidationError]


def build_error(_request: Request, exc: RequestValidationError) -> HTTPValidationError:
    return HTTPValidationError(
        detail=[ValidationError(field=".".join(map(str, error["loc"])), message=error["msg"]) for error in exc.errors()]
    )


class Item(BaseModel):
    name: str
    price: float


@app.post("/items")
async def create_item(item: Item) -> dict[str, Any]:
    return item.model_dump()


override_validation_error(app, error_builder=build_error)
