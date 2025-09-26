import json
import os

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Literal


LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
Environment = Literal["PRD", "DEV"]


class _EnvSettings(BaseSettings):
    environment: str = Field(env="ENVIRONMENT")
    secret_key: str = Field(env="SECRET_KEY")

    class Config:
        env_file = ".env"
        extra = "ignore"


class _ConsoleLoggingSettings(BaseSettings):
    enabled: bool = True
    app_level: LogLevel = "INFO"
    server_level: LogLevel = "INFO"
    use_colors: bool = True
    use_json: bool = False


class _FileLoggingSettings(BaseSettings):
    enabled: bool = False
    app_level: LogLevel = "INFO"
    server_level: LogLevel = "INFO"
    path: str | None = None
    rotate: bool = False
    max_bytes: int = 1048576  # in bytes = 1 MB
    backup_count: int = 3


class _LoggingSettings(BaseSettings):
    console: _ConsoleLoggingSettings = _ConsoleLoggingSettings()
    file: _FileLoggingSettings = _FileLoggingSettings()
    log_unhandled_exceptions: bool = True


class _HTTPServerSettings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    reload_dirs: list[str] | str | None = None
    reload_includes: list[str] | str | None = None
    reload_excludes: list[str] | str | None = None
    reload_delay: float = 0.25
    workers: int | None = None
    proxy_headers: bool = True
    server_header: bool = False
    date_header: bool = True
    forwarded_allow_ips: list[str] | str | None = None
    limit_concurrency: int | None = None
    backlog: int = 2048
    limit_max_requests: int | None = None
    timeout_keep_alive: int = 5
    timeout_graceful_shutdown: int | None = None


class _AppSettings(BaseSettings):
    title: str = "Application"
    description: str = ""
    version: str = "0.1.0"
    openapi_url: str = "/openapi.json"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    license_info: dict[str, str] | None = None


class _Settings(BaseSettings):
    app: _AppSettings
    http_server: _HTTPServerSettings
    logging: _LoggingSettings
    env: _EnvSettings


def _load_settings() -> _Settings:
    env_settings = _EnvSettings()
    
    path = f"settings_{env_settings.environment.lower()}.json"
    json_data = {}
    if os.path.exists(path):
        with open(path) as file:
            json_data = json.load(file)

    return _Settings(
        app=_AppSettings(**json_data.get("app", {})),
        http_server=_HTTPServerSettings(**json_data.get("http_server", {})),
        logging=_LoggingSettings(**json_data.get("logging", {})),
        env=env_settings,
    )


settings = _load_settings()
