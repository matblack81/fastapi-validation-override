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
    instance: str


def build_problem(request: Request, exc: RequestValidationError) -> Problem:
    return Problem(
        title="Validation failed",
        status=400,
        detail=f"{len(exc.errors())} invalid field(s)",
        instance=request.url.path,
    )


override_validation_error(
    app, error_builder=build_problem, media_type="application/problem+json"
)
# --8<-- [end:snippet]


class Item(BaseModel):
    name: str
    price: float


@app.post("/items")
def create_item(item: Item) -> Item:
    return item
