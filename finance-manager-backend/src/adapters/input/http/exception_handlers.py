import logging

from datetime import datetime, timezone
from fastapi import Request, HTTPException, FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from http import HTTPStatus
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Mapping


logger = logging.getLogger("exception_handlers")


def _response_error(
    title: str,
    status_code: int = 500,
    type_: str = "about:blank",
    detail: str | None = None,
    instance: str | None = None,
    extensions: dict | None = None,
    headers: Mapping[str, str] | None = None,
):
    content = {
        "title": title,
        "status": status_code,
        "type": type_,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if detail:
        content["detail"] = detail

    if instance:
        content["instance"] = instance

    if extensions:
        for key, value in extensions.items():
            if key in ("type", "title", "status", "detail", "instance"):
                continue
            content[key] = value

    return JSONResponse(
        content=jsonable_encoder(obj=content),
        status_code=status_code,
        headers=headers,
        media_type="application/problem+json",
    )


async def _http_exception_handler(request: Request, exc: HTTPException):
    status_code = exc.status_code if 400 <= exc.status_code <= 599 else 500
    title = HTTPStatus(status_code).phrase
    detail = exc.detail
    instance = str(request.url)
    headers = exc.headers or {}
    correlation_id = request.headers.get("X-Correlation-ID")

    if correlation_id:
        headers["correlation_id"] = correlation_id

    logger.warning(
        f"{request.method} {request.url} {status_code} - {detail}")

    return _response_error(
        title=title,
        status_code=status_code,
        # type_=type_,
        detail=detail,
        instance=instance,
        headers=headers,
    )


async def _validation_exception_handler(request: Request, exc: RequestValidationError):
    status_code = 422
    title = HTTPStatus(status_code).phrase
    detail = "Validation failed."
    instance = str(request.url)
    headers = {}
    correlation_id = request.headers.get("X-Correlation-ID")

    if correlation_id:
        headers["correlation_id"] = correlation_id

    logger.warning(
        f"{request.method} {request.url} {status_code} - Validation error")

    return _response_error(
        title=title,
        status_code=status_code,
        # type_=type_,
        detail=detail,
        instance=instance,
    )


async def _generic_exception_handler(request: Request, exc: Exception):
    status_code = 500
    title = HTTPStatus(status_code).phrase
    detail = "An unexpected error occurred."
    instance = str(request.url)
    headers = {}
    correlation_id = request.headers.get("X-Correlation-ID")

    if correlation_id:
        headers["correlation_id"] = correlation_id

    logger.exception(
        f"{request.method} {request.url} {status_code} - Unhandled error")

    return _response_error(
        title=title,
        status_code=status_code,
        # type_=type_,
        detail=detail,
        instance=instance,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)

    app.add_exception_handler(RequestValidationError,
                              _validation_exception_handler)
    app.add_exception_handler(Exception, _generic_exception_handler)
