import logging

from app.core.exception_handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.core.settings import settings
from app.routers import api_router
from fastapi import FastAPI

setup_logging()

logger = logging.getLogger("main")

logger.info("Starting application...")

app = FastAPI(
    title=settings.app.title,
    description=settings.app.description,
    version=settings.app.version,
    docs_url=settings.app.docs_url,
    redoc_url=settings.app.redoc_url,
    openapi_url=settings.app.openapi_url,
    license_info=settings.app.license_info,
)

app.include_router(api_router)
register_exception_handlers(app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
        reload_dirs=settings.server.reload_dirs,
        reload_includes=settings.server.reload_includes,
        reload_excludes=settings.server.reload_excludes,
        reload_delay=settings.server.reload_delay,
        workers=settings.server.workers,
        log_config=None,
        proxy_headers=settings.server.proxy_headers,
        server_header=settings.server.server_header,
        date_header=settings.server.date_header,
        limit_concurrency=settings.server.limit_concurrency,
        backlog=settings.server.backlog,
        limit_max_requests=settings.server.limit_max_requests,
        timeout_keep_alive=settings.server.timeout_keep_alive,
        timeout_graceful_shutdown=settings.server.timeout_graceful_shutdown,
    )
