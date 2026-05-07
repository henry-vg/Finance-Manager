from collections.abc import Generator

import pytest

from src.infra.settings.models import (
    Environment,
    FastAPISettings,
    LogSettings,
    PostgresSettings,
    Settings,
    load_settings,
)


def _set_required_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {
        "CFG_ENVIRONMENT": "PRD",
        "CFG_FASTAPI_TITLE": "Finance Manager API",
        "CFG_FASTAPI_DESCRIPTION": "The API system of a financial manager.",
        "CFG_FASTAPI_VERSION": "1.0.0",
        "CFG_FASTAPI_DOCS_URL": "/docs",
        "CFG_FASTAPI_DOCS_TITLE": "Docs - Finance Manager API",
        "CFG_FASTAPI_DOCS_DARK_MODE": "True",
        "CFG_FASTAPI_OPENAPI_URL": "/openapi.json",
        "CFG_FASTAPI_REDOC_URL": "",
        "CFG_FASTAPI_PAGINATION_DEFAULT_LIMIT": "50",
        "CFG_FASTAPI_PAGINATION_MAX_LIMIT": "500",
        "CFG_POSTGRES_HOST": "postgres",
        "CFG_POSTGRES_PORT": "5432",
        "CFG_POSTGRES_USER": "finance_manager",
        "CFG_POSTGRES_PASSWORD": "finance_manager",
        "CFG_POSTGRES_DATABASE": "finance_manager",
        "CFG_POSTGRES_ECHO": "False",
        "CFG_POSTGRES_POOL_SIZE": "10",
        "CFG_POSTGRES_MAX_OVERFLOW": "20",
        "CFG_LOG_ROOT_ENABLED": "True",
        "CFG_LOG_CONSOLE_ENABLED": "True",
        "CFG_LOG_CONSOLE_LEVEL": "DEBUG",
        "CFG_LOG_CONSOLE_UVICORN_LEVEL": "DEBUG",
        "CFG_LOG_CONSOLE_USE_COLORS": "True",
        "CFG_LOG_CONSOLE_USE_JSON": "False",
        "CFG_LOG_CONSOLE_SHOW_EXTRAS": "True",
        "CFG_LOG_CONSOLE_EXTRAS_MAX_LENGTH": "0",
        "CFG_LOG_FILE_ENABLED": "True",
        "CFG_LOG_FILE_LEVEL": "DEBUG",
        "CFG_LOG_FILE_UVICORN_LEVEL": "DEBUG",
        "CFG_LOG_FILE_PATH": "logs/finance-manager.log",
        "CFG_LOG_FILE_ROTATE": "True",
        "CFG_LOG_FILE_ROTATE_MAX_BYTES": "1048576",
        "CFG_LOG_FILE_ROTATE_BACKUP_COUNT": "5",
        "CFG_LOG_FILE_SHOW_EXTRAS": "True",
        "CFG_LOG_FILE_EXTRAS_MAX_LENGTH": "0",
        "CFG_LOG_UNHANDLED_EXCEPTIONS": "True",
    }

    for key, value in values.items():
        monkeypatch.setenv(key, value)


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Generator[None, None, None]:
    load_settings.cache_clear()
    yield
    load_settings.cache_clear()


def test_load_settings_uses_dev_env_file_by_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("CFG_ENVIRONMENT", raising=False)

    settings = load_settings()

    assert settings.environment == Environment.DEV
    assert settings.fastapi.title == "Finance Manager API"
    assert settings.fastapi.pagination_default_limit == 50
    assert settings.fastapi.pagination_max_limit == 500
    assert settings.log.console_level.value == "DEBUG"
    assert settings.postgres.host == "postgres"
    assert settings.postgres.dsn == (
        "postgresql+asyncpg://finance_manager:finance_manager@postgres:5432/"
        "finance_manager"
    )


def test_load_settings_can_be_overridden_for_local_host(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("CFG_POSTGRES_HOST", "localhost")

    settings = load_settings()

    assert settings.postgres.host == "localhost"
    assert settings.postgres.dsn == (
        "postgresql+asyncpg://finance_manager:finance_manager@localhost:5432/"
        "finance_manager"
    )


def test_load_settings_uses_process_environment_in_prd(
    monkeypatch: pytest.MonkeyPatch,
):
    _set_required_settings_env(monkeypatch)

    settings = load_settings()

    assert settings.environment == Environment.PRD
    assert settings.fastapi.docs_title == "Docs - Finance Manager API"
    assert settings.fastapi.redoc_url == ""
    assert settings.fastapi.pagination_default_limit == 50
    assert settings.fastapi.pagination_max_limit == 500
    assert settings.log.file_rotate_max_bytes == 1048576
    assert isinstance(settings, Settings)
    assert isinstance(settings.log, LogSettings)
    assert isinstance(settings.fastapi, FastAPISettings)
    assert isinstance(settings.postgres, PostgresSettings)


def test_load_settings_is_cached(monkeypatch: pytest.MonkeyPatch):
    _set_required_settings_env(monkeypatch)

    first = load_settings()
    monkeypatch.setenv("CFG_FASTAPI_TITLE", "Changed Title")

    second = load_settings()

    assert first is second
    assert second.fastapi.title == "Finance Manager API"
    assert second.postgres.database == "finance_manager"
