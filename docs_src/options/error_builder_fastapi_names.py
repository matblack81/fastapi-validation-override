from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from fastapi_validation_override import override_validation_error

app = FastAPI()


# --8<-- [start:snippet]
class ValidationError(BaseModel):
    field: str
    message: str


class HTTPValidationError(BaseModel):
    detail: list[ValidationError]


def build_error(
    _request: Request, exc: RequestValidationError
) -> HTTPValidationError:
    return HTTPValidationError(
        detail=[
            ValidationError(
                field=".".join(map(str, e["loc"])), message=e["msg"]
            )
            for e in exc.errors()
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
