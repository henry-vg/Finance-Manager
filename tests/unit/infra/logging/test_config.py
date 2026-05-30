import builtins
import logging
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

from src.infra.logging import config as logging_config
from src.infra.settings.models import (
    Environment,
    FastAPISettings,
    LogLevel,
    LogSettings,
    PostgresSettings,
    Settings,
)


def _build_settings(
    *,
    console_enabled: bool = True,
    console_use_json: bool = False,
    console_use_colors: bool = False,
    file_enabled: bool = False,
    file_path: str = "logs/finance-manager.log",
    file_rotate: bool = True,
    unhandled_exceptions: bool = True,
) -> Settings:
    return Settings(
        environment=Environment.DEV,
        postgres=PostgresSettings(
            host="localhost",
            port=5432,
            user="finance_manager",
            password="finance_manager",
            database="finance_manager",
            echo=False,
            pool_size=10,
            max_overflow=20,
        ),
        log=LogSettings(
            root_enabled=True,
            console_enabled=console_enabled,
            console_level=LogLevel.DEBUG,
            console_uvicorn_level=LogLevel.INFO,
            console_use_colors=console_use_colors,
            console_use_json=console_use_json,
            console_show_extras=True,
            console_extras_max_length=0,
            file_enabled=file_enabled,
            file_level=LogLevel.INFO,
            file_uvicorn_level=LogLevel.WARNING,
            file_path=file_path,
            file_rotate=file_rotate,
            file_rotate_max_bytes=1024,
            file_rotate_backup_count=3,
            file_show_extras=True,
            file_extras_max_length=0,
            unhandled_exceptions=unhandled_exceptions,
        ),
        fastapi=FastAPISettings(
            title="Finance Manager API",
            description="The API system of a financial manager.",
            version="1.0.0",
            docs_url="/docs",
            docs_title="Docs - Finance Manager API",
            docs_dark_mode=True,
            openapi_url="/openapi.json",
            redoc_url="",
            pagination_default_limit=50,
            pagination_max_limit=500,
        ),
    )


def test_remove_extras_filter_removes_known_extra_fields() -> None:
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="message",
        args=(),
        exc_info=None,
    )
    record.color_message = "colorized"
    record.levelprefix = "INFO"

    result = logging_config.RemoveExtrasFilter().filter(record)

    assert result is True
    assert not hasattr(record, "color_message")
    assert not hasattr(record, "levelprefix")


def test_show_extras_filter_hides_extras_when_disabled() -> None:
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="message",
        args=(),
        exc_info=None,
    )
    record.trace_id = "trace-123"

    result = logging_config.ShowExtrasFilter(show=False, max_length=0).filter(record)
    record_with_extras = cast(Any, record)

    assert result is True
    assert record_with_extras.extras == ""


def test_show_extras_filter_formats_and_truncates_visible_extras() -> None:
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="message",
        args=(),
        exc_info=None,
    )
    record.trace_id = "trace-123"
    record.route_path = "/healthz/liveness"

    result = logging_config.ShowExtrasFilter(show=True, max_length=25).filter(record)
    record_with_extras = cast(Any, record)

    assert result is True
    extras = record_with_extras.extras

    assert extras.startswith("[")
    assert extras.endswith("…]")
    assert "route_path=" in extras


def test_setup_logging_falls_back_to_console_and_registers_excepthook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_config: dict[str, Any] = {}
    original_excepthook = logging_config.sys.excepthook

    monkeypatch.setattr(
        logging_config,
        "dictConfig",
        lambda config: captured_config.update(config),
    )
    monkeypatch.setattr(logging_config.sys, "excepthook", original_excepthook)

    try:
        logging_config.setup_logging(
            _build_settings(console_enabled=False, file_enabled=False),
        )

        assert captured_config["handlers"].keys() == {"console_stream"}
        assert captured_config["root"]["handlers"] == ["console_stream"]
        assert logging_config.sys.excepthook is not original_excepthook
    finally:
        logging_config.sys.excepthook = original_excepthook


@pytest.mark.parametrize(
    ("file_rotate", "expected_handler_class"),
    [
        (True, "logging.handlers.RotatingFileHandler"),
        (False, "logging.FileHandler"),
    ],
)
def test_setup_logging_configures_file_handler_variants(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    file_rotate: bool,
    expected_handler_class: str,
) -> None:
    captured_config: dict[str, Any] = {}
    file_path = tmp_path / "logs" / "finance-manager.log"

    monkeypatch.setattr(
        logging_config,
        "dictConfig",
        lambda config: captured_config.update(config),
    )

    logging_config.setup_logging(
        _build_settings(
            console_enabled=False,
            file_enabled=True,
            file_path=str(file_path),
            file_rotate=file_rotate,
            unhandled_exceptions=False,
        ),
    )

    assert file_path.parent.exists()
    assert captured_config["handlers"]["file"]["class"] == expected_handler_class
    assert captured_config["root"]["handlers"] == ["file"]


def test_show_extras_filter_returns_empty_string_when_no_visible_extras() -> None:
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="message",
        args=(),
        exc_info=None,
    )

    result = logging_config.ShowExtrasFilter(show=True, max_length=0).filter(record)
    record_with_extras = cast(Any, record)

    assert result is True
    assert record_with_extras.extras == ""


def test_setup_logging_configures_console_json_formatter_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_config: dict[str, Any] = {}
    fake_pythonjsonlogger = cast(Any, ModuleType("pythonjsonlogger"))
    fake_pythonjsonlogger.jsonlogger = object()

    monkeypatch.setitem(
        logging_config.sys.modules,
        "pythonjsonlogger",
        fake_pythonjsonlogger,
    )

    monkeypatch.setattr(
        logging_config,
        "dictConfig",
        lambda config: captured_config.update(config),
    )

    logging_config.setup_logging(
        _build_settings(
            console_use_json=True,
            unhandled_exceptions=False,
        ),
    )

    assert "console_json" in captured_config["formatters"]
    assert captured_config["handlers"]["console_stream"]["formatter"] == "console_json"


def test_setup_logging_prefers_json_over_colors_when_both_are_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_config: dict[str, Any] = {}
    fake_pythonjsonlogger = cast(Any, ModuleType("pythonjsonlogger"))
    fake_pythonjsonlogger.jsonlogger = object()

    monkeypatch.setitem(
        logging_config.sys.modules,
        "pythonjsonlogger",
        fake_pythonjsonlogger,
    )
    monkeypatch.setattr(
        logging_config,
        "dictConfig",
        lambda config: captured_config.update(config),
    )

    logging_config.setup_logging(
        _build_settings(
            console_use_json=True,
            console_use_colors=True,
            unhandled_exceptions=False,
        ),
    )

    assert captured_config["handlers"]["console_stream"]["formatter"] == "console_json"
    assert "console_color" not in captured_config["formatters"]


def test_setup_logging_configures_console_color_formatter_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_config: dict[str, Any] = {}
    fake_colorlog = cast(Any, ModuleType("colorlog"))
    fake_colorlog.ColoredFormatter = object()

    monkeypatch.setitem(logging_config.sys.modules, "colorlog", fake_colorlog)

    monkeypatch.setattr(
        logging_config,
        "dictConfig",
        lambda config: captured_config.update(config),
    )

    logging_config.setup_logging(
        _build_settings(
            console_use_colors=True,
            unhandled_exceptions=False,
        ),
    )

    assert "console_color" in captured_config["formatters"]
    assert captured_config["handlers"]["console_stream"]["formatter"] == "console_color"


def test_setup_logging_falls_back_when_json_formatter_import_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_config: dict[str, Any] = {}
    original_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "pythonjsonlogger":
            raise ImportError("missing optional dependency")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(
        logging_config,
        "dictConfig",
        lambda config: captured_config.update(config),
    )

    logging_config.setup_logging(
        _build_settings(
            console_use_json=True,
            unhandled_exceptions=False,
        ),
    )

    assert captured_config["handlers"]["console_stream"]["formatter"] == "file_plain"


def test_setup_logging_falls_back_when_color_formatter_import_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_config: dict[str, Any] = {}
    original_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "colorlog":
            raise ImportError("missing optional dependency")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(
        logging_config,
        "dictConfig",
        lambda config: captured_config.update(config),
    )

    logging_config.setup_logging(
        _build_settings(
            console_use_colors=True,
            unhandled_exceptions=False,
        ),
    )

    assert captured_config["handlers"]["console_stream"]["formatter"] == "file_plain"


def test_setup_logging_unhandled_exception_hook_logs_non_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_calls: list[tuple[str, Any]] = []
    original_excepthook = logging_config.sys.excepthook

    monkeypatch.setattr(logging_config, "dictConfig", lambda config: None)
    monkeypatch.setattr(
        logging.Logger,
        "critical",
        lambda self, message, exc_info=None: captured_calls.append((message, exc_info)),
    )

    try:
        logging_config.setup_logging(_build_settings(unhandled_exceptions=True))
        exc = RuntimeError("boom")
        logging_config.sys.excepthook(RuntimeError, exc, None)
    finally:
        logging_config.sys.excepthook = original_excepthook

    assert captured_calls == [
        (
            "UNHANDLED EXCEPTION",
            (RuntimeError, exc, None),
        ),
    ]


def test_setup_logging_unhandled_exception_hook_delegates_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delegated_calls: list[tuple[object, object, object]] = []
    original_excepthook = logging_config.sys.excepthook

    def fake_system_excepthook(
        exc_type: object,
        exc_value: object,
        exc_traceback: object,
    ) -> None:
        delegated_calls.append((exc_type, exc_value, exc_traceback))

    monkeypatch.setattr(logging_config, "dictConfig", lambda config: None)
    monkeypatch.setattr(logging_config.sys, "__excepthook__", fake_system_excepthook)

    try:
        logging_config.setup_logging(_build_settings(unhandled_exceptions=True))
        exc = KeyboardInterrupt()
        logging_config.sys.excepthook(KeyboardInterrupt, exc, None)
    finally:
        logging_config.sys.excepthook = original_excepthook

    assert delegated_calls == [(KeyboardInterrupt, exc, None)]
