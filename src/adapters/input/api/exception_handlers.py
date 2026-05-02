import json
import logging
from datetime import (
    datetime,
)
from http import HTTPStatus

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(name=__name__)


def _response_error(
    title: str,
    status_code: int = 500,
    type_: str | None = None,
    detail: str | None = None,
    instance: str | None = None,
    extensions: dict | None = None,
    headers: dict[str, str] | None = None,
    trace_id: str | None = None,
) -> JSONResponse:
    status_code = status_code if 400 <= status_code <= 599 else 500

    content = {
        "title": title,
        "status": status_code,
        "type": type_ or "about:blank",
        "timestamp": datetime.now(
            tz=datetime.UTC,
        )
        .isoformat(
            timespec="milliseconds",
        )
        .replace(
            old="+00:00",
            new="Z",
        ),
    }

    if detail:
        content["detail"] = (
            detail if isinstance(detail, str) else json.dumps(obj=detail)
        )

    if instance:
        content["instance"] = instance

    if extensions:
        for key, value in extensions.items():
            if key not in (
                "type",
                "title",
                "status",
                "detail",
                "instance",
            ):
                content[key] = value

    content["trace_id"] = trace_id

    return JSONResponse(
        content=jsonable_encoder(obj=content),
        status_code=status_code,
        media_type="application/problem+json",
        headers=headers,
    )


async def _http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    status_code = exc.status_code if 400 <= exc.status_code <= 599 else 500
    title = HTTPStatus(value=status_code).phrase
    detail = (
        exc.detail if isinstance(exc.detail, str | None) else json.dumps(obj=exc.detail)
    )
    instance = str(object=request.url)

    logger.warning(msg=f"{request.method} {request.url} {status_code} - {detail}")

    return _response_error(
        title=title,
        status_code=status_code,
        # type_=type_,
        detail=detail,
        instance=instance,
        trace_id=request.headers.get("X-Trace-Id"),
    )


async def _validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = exc.errors()

    BODY_LIKE_LOCATIONS = ("body", "form", "file")

    if errors and all(
        (error.get("loc", [""]) or [""])[0] in BODY_LIKE_LOCATIONS for error in errors
    ):
        status_code = 422
        title = HTTPStatus(value=status_code).phrase
        detail = "Validation failed."
    else:
        status_code = 400
        title = HTTPStatus(value=status_code).phrase
        detail = "Invalid request."

    instance = str(object=request.url)

    logger.warning(
        msg=f"{request.method} {request.url} {status_code} - {detail} - {errors}"
    )

    return _response_error(
        title=title,
        status_code=status_code,
        # type_=type_,
        detail=detail,
        instance=instance,
        trace_id=request.headers.get("X-Trace-Id"),
        extensions={"errors": errors},
    )


async def _generic_exception_handler(
    request: Request,
    _: Exception,
) -> JSONResponse:
    status_code = 500
    title = HTTPStatus(value=status_code).phrase
    detail = "An unexpected error occurred."
    instance = str(object=request.url)

    logger.exception(
        msg=f"{request.method} {request.url} {status_code} - Unhandled error"
    )

    return _response_error(
        title=title,
        status_code=status_code,
        # type_=type_,
        detail=detail,
        instance=instance,
        trace_id=request.headers.get("X-Trace-Id"),
    )


def add_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        exc_class_or_status_code=HTTPException,
        handler=_http_exception_handler,
    )
    app.add_exception_handler(
        exc_class_or_status_code=StarletteHTTPException,
        handler=_http_exception_handler,
    )
    app.add_exception_handler(
        exc_class_or_status_code=RequestValidationError,
        handler=_validation_exception_handler,
    )
    app.add_exception_handler(
        exc_class_or_status_code=Exception,
        handler=_generic_exception_handler,
    )
