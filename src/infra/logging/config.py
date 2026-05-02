import logging
import sys
from datetime import UTC, datetime
from logging.config import dictConfig
from pathlib import Path

from src.infra.settings import Settings


class RemoveExtrasFilter(logging.Filter):
    EXTRAS_TO_REMOVE = (
        "color_message",
        "levelprefix",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        for key in self.EXTRAS_TO_REMOVE:
            if hasattr(record, key):
                delattr(record, key)
        return True


class ShowExtrasFilter(logging.Filter):
    _EXTRAS_TO_IGNORE = (
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
        "timestamp",
        "service",
        "env",
        "stacklevel",
        "taskName",
        "color_message",
        "levelprefix",
        "client_addr",
        "request_line",
        "extras",
    )

    def __init__(
        self,
        show: bool,
        max_length: int,
    ) -> None:
        super().__init__()
        self._show: bool = show
        self._max_length = max_length

    def filter(self, record: logging.LogRecord) -> bool:
        if not self._show:
            record.extras = ""
            return True

        record_dict = record.__dict__
        keys = [
            key
            for key in record_dict.keys()
            if key not in self._EXTRAS_TO_IGNORE and not key.startswith("_")
        ]
        if not keys:
            record.extras = ""
            return True

        keys.sort()
        extras = " ".join([f"{key}={repr(record_dict[key])}" for key in keys])
        extras = (
            extras[: self._max_length - 1] + "…"
            if 0 < self._max_length < len(extras)
            else extras
        )

        record.extras = f"[{extras}]"

        return True


def setup_logging(settings: Settings) -> None:
    logging.Formatter.formatTime = lambda self, record, datefmt=None: (
        datetime.fromtimestamp(record.created, tz=UTC)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )

    console_enabled = settings.log.console_enabled
    file_enabled = settings.log.file_enabled and settings.log.file_path

    if not console_enabled and not file_enabled:
        console_enabled = True

    console_use_json = settings.log.console_use_json
    console_use_colors = settings.log.console_use_colors

    if console_use_json and console_use_colors:
        console_use_colors = False

    formatters = {}

    formatters["file_plain"] = {
        "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s %(extras)s",
    }
    formatter_name = "file_plain"

    if console_enabled and console_use_json:
        try:
            from pythonjsonlogger import jsonlogger  # noqa
        except Exception:
            console_use_json = False

    if console_enabled and console_use_json:
        formatters["console_json"] = {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": ("%(asctime)s %(levelname)s %(name)s %(message)s"),
        }
        formatter_name = "console_json"
    elif console_enabled and console_use_colors:
        try:
            from colorlog import ColoredFormatter  # noqa
        except Exception:
            console_use_colors = False

    if console_enabled and console_use_colors:
        formatters["console_color"] = {
            "()": "colorlog.ColoredFormatter",
            "format": (
                "%(cyan)s%(asctime)s%(reset)s "
                "%(log_color)s[%(levelname)s]%(reset)s "
                "%(purple)s%(name)s:%(reset)s "
                "%(message)s "
                "%(extras)s"
            ),
            "log_colors": {
                "DEBUG": "bold_purple",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        }
        formatter_name = "console_color"

    handlers = {}
    handler_names = []

    if console_enabled:
        handlers["console_stream"] = {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": formatter_name,
            "level": settings.log.console_level,
            "filters": ["remove_extras", "extras_console"],
        }
        handler_names.append("console_stream")

    if file_enabled:
        file_path = settings.log.file_path
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        if settings.log.file_rotate:
            handlers["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": file_path,
                "mode": "a",
                "formatter": "file_plain",
                "level": settings.log.file_level,
                "maxBytes": settings.log.file_rotate_max_bytes,
                "backupCount": settings.log.file_rotate_backup_count,
                "encoding": "utf-8",
                "filters": ["remove_extras", "extras_file"],
            }
        else:
            handlers["file"] = {
                "class": "logging.FileHandler",
                "filename": file_path,
                "mode": "a",
                "formatter": "file_plain",
                "level": settings.log.file_level,
                "encoding": "utf-8",
                "filters": ["remove_extras", "extras_file"],
            }
        handler_names.append("file")

    filters = {
        "remove_extras": {"()": RemoveExtrasFilter},
        "extras_console": {
            "()": ShowExtrasFilter,
            "show": settings.log.console_show_extras,
            "max_length": settings.log.console_extras_max_length,
        },
        "extras_file": {
            "()": ShowExtrasFilter,
            "show": settings.log.file_show_extras,
            "max_length": settings.log.file_extras_max_length,
        },
    }

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": not settings.log.root_enabled,
            "formatters": formatters,
            "handlers": handlers,
            "filters": filters,
            "root": {
                "level": "DEBUG",
                "handlers": handler_names if settings.log.root_enabled else [],
            },
            "loggers": {
                "src": {
                    "handlers": handler_names,
                    "level": "DEBUG",
                    "propagate": False,
                },
                "uvicorn.error": {
                    "handlers": handler_names,
                    "level": (
                        settings.log.console_uvicorn_level
                        if settings.log.console_enabled
                        else settings.log.file_uvicorn_level
                    ),
                    "propagate": False,
                },
            },
        },
    )

    def handle_unhandled_exception(
        exc_type,
        exc_value,
        exc_traceback,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger = logging.getLogger("exception.unhandled")
        logger.critical(
            "UNHANDLED EXCEPTION", exc_info=(exc_type, exc_value, exc_traceback),
        )

    if settings.log.unhandled_exceptions:
        sys.excepthook = handle_unhandled_exception
