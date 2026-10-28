from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi_validation_override import override_validation_error
from pydantic import BaseModel

app = FastAPI()


# --8<-- [start:snippet]
class FieldError(BaseModel):
    field: str
    message: str


class ErrorEnvelope(BaseModel):
    code: str = "VALIDATION_ERROR"
    errors: list[FieldError]


def build_error(exc: RequestValidationError) -> ErrorEnvelope:
    return ErrorEnvelope(
        errors=[
            FieldError(
                field=".".join(map(str, error["loc"])), message=error["msg"]
            )
            for error in exc.errors()
        ]
    )


override_validation_error(app, error_builder=build_error)
# --8<-- [end:snippet]


class Item(BaseModel):
    name: str
    price: float


@app.post("/items")
def create_item(item: Item) -> Item:
    return item


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
