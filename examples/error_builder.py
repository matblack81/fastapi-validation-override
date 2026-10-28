"""
Replace the validation error body and its schema with your own Pydantic model.

Run:

    uvicorn examples.error_builder:app --reload
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from fastapi_validation_override import override_validation_error

app = FastAPI(
    title="Error Builder Example",
    description="Validation errors are returned and documented as ErrorEnvelope at 400.",
)


class FieldError(BaseModel):
    field: str
    message: str


class ErrorEnvelope(BaseModel):
    code: str = "VALIDATION_ERROR"
    errors: list[FieldError]


def build_error(_request: Request, exc: RequestValidationError) -> ErrorEnvelope:
    return ErrorEnvelope(
        errors=[FieldError(field=".".join(map(str, error["loc"])), message=error["msg"]) for error in exc.errors()]
    )


class Item(BaseModel):
    name: str
    price: float


@app.post("/items")
async def create_item(item: Item) -> dict[str, Any]:
    return item.model_dump()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


override_validation_error(app, error_builder=build_error)
