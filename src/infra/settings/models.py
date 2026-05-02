from enum import StrEnum

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
        env_file="docker/dev/.env",
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
        env_file="docker/dev/.env",
    )

    title: str
    description: str
    version: str
    docs_url: str
    docs_title: str
    docs_dark_mode: bool
    openapi_url: str
    redoc_url: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CFG_",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
        env_file="docker/dev/.env",
    )

    environment: Environment

    log: LogSettings = LogSettings()
    fastapi: FastAPISettings = FastAPISettings()


def load_settings() -> Settings:
    return Settings()
