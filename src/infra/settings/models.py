import os
from enum import StrEnum
from functools import lru_cache

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Environment(StrEnum):
    PRD = "PRD"
    DEV = "DEV"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CFG_LOG_",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    root_enabled: bool
    console_enabled: bool
    console_level: LogLevel
    console_uvicorn_level: LogLevel
    console_use_colors: bool
    console_use_json: bool
    console_show_extras: bool
    console_extras_max_length: int
    file_enabled: bool
    file_level: LogLevel
    file_uvicorn_level: LogLevel
    file_path: str
    file_rotate: bool
    file_rotate_max_bytes: int
    file_rotate_backup_count: int
    file_show_extras: bool
    file_extras_max_length: int
    unhandled_exceptions: bool


class FastAPISettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CFG_FASTAPI_",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    title: str
    description: str
    version: str
    docs_url: str
    docs_title: str
    docs_dark_mode: bool
    openapi_url: str
    redoc_url: str


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CFG_POSTGRES_",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    host: str
    port: int
    user: str
    password: str
    database: str
    echo: bool
    pool_size: int
    max_overflow: int

    @property
    def dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CFG_",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    environment: Environment

    log: LogSettings
    fastapi: FastAPISettings
    postgres: PostgresSettings


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    env_file = (
        "docker/dev/.env"
        if os.getenv("CFG_ENVIRONMENT", Environment.DEV.value) == Environment.DEV.value
        else None
    )

    return Settings(
        _env_file=env_file,
        log=LogSettings(_env_file=env_file),
        fastapi=FastAPISettings(_env_file=env_file),
        postgres=PostgresSettings(_env_file=env_file),
    )
