"""
Logging configuration for Condomínios Manager.

Enterprise-grade logging with:
- Structured logging
- File rotation
- Separate log files for different levels
- Request/response logging
- Performance tracking
- Windows-safe file rotation (handles permission errors)
"""

import logging.handlers
import sys
from pathlib import Path


class WindowsSafeRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """
    Windows-safe rotating file handler.

    Handles PermissionError that occurs on Windows when multiple processes
    try to rotate the same log file simultaneously.
    """

    def doRollover(self):
        """
        Do a rollover, catching Windows permission errors.

        If rotation fails due to PermissionError (file in use by another process),
        silently continue without rotating. The file will be rotated on the next
        attempt when no other process is using it.
        """
        try:
            super().doRollover()
        except PermissionError:
            # File is locked by another process (common on Windows with pytest)
            # Skip rotation this time - will try again next time
            pass
        except OSError as e:
            # Catch other OS errors during rotation
            if e.errno == 13:  # Permission denied
                pass
            else:
                raise


# Determine which handler to use based on platform
if sys.platform == "win32":
    # Use Windows-safe handler on Windows
    ROTATING_HANDLER_CLASS = "condominios_manager.logging_config.WindowsSafeRotatingFileHandler"
else:
    # Use standard handler on Unix/Linux/Mac
    ROTATING_HANDLER_CLASS = "logging.handlers.RotatingFileHandler"


# Base directory for logs
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"

# Create logs directory if it doesn't exist
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file_debug": {
            "level": "DEBUG",
            "class": ROTATING_HANDLER_CLASS,
            "filename": LOG_DIR / "debug.log",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "file_info": {
            "level": "INFO",
            "class": ROTATING_HANDLER_CLASS,
            "filename": LOG_DIR / "info.log",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "file_error": {
            "level": "ERROR",
            "class": ROTATING_HANDLER_CLASS,
            "filename": LOG_DIR / "error.log",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
            "formatter": "verbose",
        },
        "file_security": {
            "level": "WARNING",
            "class": ROTATING_HANDLER_CLASS,
            "filename": LOG_DIR / "security.log",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
            "formatter": "json",
        },
        "file_access": {
            "level": "INFO",
            "class": ROTATING_HANDLER_CLASS,
            "filename": LOG_DIR / "access.log",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 5,
            "formatter": "json",
        },
        "file_performance": {
            "level": "INFO",
            "class": ROTATING_HANDLER_CLASS,
            "filename": LOG_DIR / "performance.log",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 5,
            "formatter": "json",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file_info", "file_error"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["file_error"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["file_security"],
            "level": "WARNING",
            "propagate": False,
        },
        "core": {
            "handlers": ["console", "file_debug", "file_info", "file_error"],
            "level": "DEBUG",
            "propagate": False,
        },
        "access": {
            "handlers": ["file_access"],
            "level": "INFO",
            "propagate": False,
        },
        "performance": {
            "handlers": ["file_performance"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "file_info", "file_error"],
        "level": "INFO",
    },
}
