from src.infra.server import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    from src.infra.settings import settings

    uvicorn.run(
        "src.infra.server:create_app",
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
        factory=True,
    )
