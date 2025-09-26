if __name__ == "__main__":
    import uvicorn
    from src.infra.settings import settings

    uvicorn.run(
        app="src.infra.http_server:create_app",
        host=settings.http_server.host,
        port=settings.http_server.port,
        reload=settings.http_server.reload,
        reload_dirs=settings.http_server.reload_dirs,
        reload_includes=settings.http_server.reload_includes,
        reload_excludes=settings.http_server.reload_excludes,
        reload_delay=settings.http_server.reload_delay,
        workers=settings.http_server.workers,
        log_config=None,
        proxy_headers=settings.http_server.proxy_headers,
        server_header=settings.http_server.server_header,
        date_header=settings.http_server.date_header,
        forwarded_allow_ips=settings.http_server.forwarded_allow_ips,
        limit_concurrency=settings.http_server.limit_concurrency,
        backlog=settings.http_server.backlog,
        limit_max_requests=settings.http_server.limit_max_requests,
        timeout_keep_alive=settings.http_server.timeout_keep_alive,
        timeout_graceful_shutdown=settings.http_server.timeout_graceful_shutdown,
        factory=True,
    )
