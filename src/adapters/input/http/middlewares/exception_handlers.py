import logging

from fastapi import Request, HTTPException, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException


logger = logging.getLogger("exception_handlers")


async def _http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(
        f"{request.method} {request.url} {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


async def _validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        f"{request.method} {request.url} 422 - Validation error - {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": f"Validation error"},
    )


async def _generic_exception_handler(request: Request, exc: Exception):
    logger.exception(f"{request.method} {request.url} 500 - Unhandled error")
    return JSONResponse(
        status_code=500,
        content={"error": f"Internal server error"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)

    app.add_exception_handler(RequestValidationError,
                              _validation_exception_handler)
    app.add_exception_handler(Exception, _generic_exception_handler)
