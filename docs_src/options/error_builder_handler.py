from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from fastapi_validation_override import override_validation_error

app = FastAPI()


class FieldError(BaseModel):
    field: str
    message: str


class ErrorEnvelope(BaseModel):
    code: str = "VALIDATION_ERROR"
    errors: list[FieldError]


def build_error(exc: RequestValidationError) -> ErrorEnvelope:
    return ErrorEnvelope(
        errors=[
            FieldError(field=".".join(map(str, e["loc"])), message=e["msg"])
            for e in exc.errors()
        ]
    )


# --8<-- [start:snippet]
@app.exception_handler(RequestValidationError)
async def validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=jsonable_encoder(build_error(exc)),
        headers={"Content-Language": "en"},
    )


override_validation_error(
    app, handle_exceptions=False, error_builder=build_error
)
# --8<-- [end:snippet]


class Item(BaseModel):
    name: str
    price: float


@app.post("/items")
def create_item(item: Item) -> Item:
    return item
