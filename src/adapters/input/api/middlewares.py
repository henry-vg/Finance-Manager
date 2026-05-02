import logging
import time

from fastapi import FastAPI, Request, Response

logger = logging.getLogger(__name__)


def add_middlewares(app: FastAPI) -> None:
    @app.middleware("http")
    async def log_request_and_response(request: Request, call_next):
        request_extra = {
            "address": f"{request.client.host}:{request.client.port}",
            "method": request.method,
            "http_version": f"HTTP/{request.scope.get('http_version')}",
        }

        logger.info(
            "Request received. Processing...",
            extra=request_extra,
        )

        start = time.perf_counter()

        response: Response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 4)

        response_extra = {
            "address": f"{request.client.host}:{request.client.port}",
            "method": request.method,
            "http_version": f"HTTP/{request.scope.get('http_version')}",
            "status_code": response.status_code,
            "process_duration_ms": duration_ms,
        }

        request_scope_route = request.scope.get("route")
        if hasattr(request_scope_route, "path"):
            response_extra["route_path"] = request_scope_route.path

        logger.info(
            "Response sent",
            extra=response_extra,
        )

        return response

    @app.middleware("http")
    async def add_trace_id_header(request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Trace-Id"] = request.headers.get("X-Trace-Id") or ""
        return response
