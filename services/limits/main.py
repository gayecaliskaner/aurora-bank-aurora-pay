"""Aurora Limits & Statements: transfer limits, authorization and statements API."""

import logging
from typing import Annotated

from fastapi import FastAPI, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import service
from .models import (
    AuthorizeInput,
    Decision,
    IsoDate,
    Limits,
    LimitsInput,
    Statement,
    ValidationFailure,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Aurora Limits & Statements", version="1.0.0")

CustomerId = Annotated[str, Path(pattern=r"^C[0-9]{6}$")]

_HTTP_ERROR_CODES = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}


def _envelope(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


@app.exception_handler(RequestValidationError)
async def _request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    parts = []
    for err in exc.errors():
        location = ".".join(str(p) for p in err.get("loc", ()) if p != "body")
        message = err.get("msg", "invalid value")
        parts.append(f"{location}: {message}" if location else message)
    return _envelope(422, "VALIDATION_ERROR", "; ".join(parts) or "Invalid request")


@app.exception_handler(ValidationFailure)
async def _validation_failure_handler(request: Request, exc: ValidationFailure) -> JSONResponse:
    return _envelope(422, "VALIDATION_ERROR", str(exc) or "Invalid request")


@app.exception_handler(StarletteHTTPException)
async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _HTTP_ERROR_CODES.get(exc.status_code, "HTTP_ERROR")
    return _envelope(exc.status_code, code, "Request could not be processed")


@app.exception_handler(Exception)
async def _unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return _envelope(500, "INTERNAL_ERROR", "Beklenmeyen bir hata oluştu")


@app.put("/limits/{customer_id}", response_model=Limits)
def put_limits(customer_id: CustomerId, data: LimitsInput):
    return service.set_limits(customer_id, data)


@app.get("/limits/{customer_id}", response_model=Limits)
def get_limits(customer_id: CustomerId):
    return service.get_limits(customer_id)


@app.post("/limits/{customer_id}/authorize", response_model=Decision)
def authorize(customer_id: CustomerId, data: AuthorizeInput):
    return service.authorize(customer_id, data)


@app.get("/statements/{customer_id}", response_model=Statement, response_model_by_alias=True)
def get_statement(
    customer_id: CustomerId,
    from_: Annotated[IsoDate, Query(alias="from")],
    to: Annotated[IsoDate, Query()],
):
    return service.get_statement(customer_id, from_, to)
