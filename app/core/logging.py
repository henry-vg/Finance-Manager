import logging
import sys

from logging.config import dictConfig
from pathlib import Path
from app.core.settings import settings


def setup_logging():
    handlers = {}
    formatter_defs = {}
    handler_names = []

    formatter_defs["file_plain"] = {
        "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    }

    if settings.logging.console.enabled:
        console = settings.logging.console

        formatter_name = "file_plain"

        if console.use_json:
            # Aqui, o "jsonlogger" é carregado implicitamente, necessário mantê-lo
            from pythonjsonlogger import jsonlogger

            formatter_defs["console_json"] = {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s"
            }
            formatter_name = "console_json"
        elif console.use_colors:
            # Aqui, o "ColoredFormatter" é carregado implicitamente, necessário mantê-lo
            from colorlog import ColoredFormatter

            formatter_defs["console_color"] = {
                "()": "colorlog.ColoredFormatter",
                "format": "%(black)s%(asctime)s%(reset)s %(log_color)s[%(levelname)s]%(reset)s %(light_yellow)s%(name)s:%(reset)s %(message)s",
                "log_colors": {
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red"
                }
            }
            formatter_name = "console_color"

        handlers["console"] = {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": formatter_name,
            "level": console.app_level
        }
        handler_names.append("console")

    if settings.logging.file.enabled and settings.logging.file.path:
        file = settings.logging.file

        Path(file.path).parent.mkdir(parents=True, exist_ok=True)

        if file.rotate:
            handlers["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": file.path,
                "mode": "a",
                "formatter": "file_plain",
                "level": file.app_level,
                "maxBytes": file.max_bytes,
                "backupCount": file.backup_count
            }
        else:
            handlers["file"] = {
                "class": "logging.FileHandler",
                "filename": file.path,
                "mode": "a",
                "formatter": "file_plain",
                "level": file.app_level
            }

        handler_names.append("file")

    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatter_defs,
        "handlers": handlers,
        "root": {
            "level": "DEBUG",  # root precisa aceitar todos, handlers filtram
            "handlers": handler_names
        },
        "loggers": {
            "uvicorn.error": {
                "handlers": handler_names,
                "level": settings.logging.console.server_level
                if settings.logging.console.enabled else settings.logging.file.server_level,
                "propagate": False
            },
            "uvicorn.access": {
                "handlers": handler_names,
                "level": settings.logging.console.server_level
                if settings.logging.console.enabled else settings.logging.file.server_level,
                "propagate": False
            }
        }
    })


def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger = logging.getLogger("exception.unhandled")
    logger.critical("UNHANDLED EXCEPTION", exc_info=(
        exc_type, exc_value, exc_traceback))


if settings.logging.log_unhandled_exceptions:
    sys.excepthook = handle_unhandled_exception
