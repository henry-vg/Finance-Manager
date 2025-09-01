import json
import os

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional, Literal


class _EnvSettings(BaseSettings):
    secret_key: str = Field(env="SECRET_KEY")

    class Config:
        env_file = ".env"
        extra = "ignore"


LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


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
    path: Optional[str] = None
    rotate: bool = False
    max_bytes: int = 1048576  # em bytes = 1 MB
    backup_count: int = 3


class _LoggingSettings(BaseSettings):
    console: _ConsoleLoggingSettings = _ConsoleLoggingSettings()
    file: _FileLoggingSettings = _FileLoggingSettings()
    log_unhandled_exceptions: bool = True


class _ServerSettings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    reload_dirs: Optional[list[str] | str] = None
    reload_includes: Optional[list[str] | str] = None
    reload_excludes: Optional[list[str] | str] = None
    reload_delay: float = 0.25
    workers: Optional[int] = None
    proxy_headers: bool = True
    server_header: bool = False
    date_header: bool = True
    limit_concurrency: Optional[int] = None
    backlog: int = 2048
    limit_max_requests: Optional[int] = None
    timeout_keep_alive: int = 5
    timeout_graceful_shutdown: Optional[int] = None


class _AppSettings(BaseSettings):
    title: str = "Application"
    description: str = ""
    version: str = "0.1.0"
    openapi_url: str = "/openapi.json"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    license_info: Optional[dict[str, str]] = None


class _Settings(BaseSettings):
    app: _AppSettings
    server: _ServerSettings
    logging: _LoggingSettings
    env: _EnvSettings = _EnvSettings()


def _load_settings() -> _Settings:
    path = "settings.json"
    json_data = {}
    if os.path.exists(path):
        with open(path) as file:
            json_data = json.load(file)

    return _Settings(
        app=_AppSettings(**json_data.get("app", {})),
        server=_ServerSettings(**json_data.get("server", {})),
        logging=_LoggingSettings(**json_data.get("logging", {}))
    )


settings = _load_settings()
