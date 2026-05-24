"""
Core Logger — Structured Contextual Logging

Provides a premium, colored standard library-based logging format
for both core operations and dynamic plugins. Compatible with standard LoggerAdapter typing.
"""

import logging
import sys
from typing import Any


class OmniLogger(logging.LoggerAdapter):
    """Custom LoggerAdapter that natively supports loguru-style .bind()"""

    def bind(self, **kwargs: Any) -> "OmniLogger":
        new_extra = {**(self.extra or {}), **kwargs}
        return OmniLogger(self.logger, new_extra)

    def set_level(self, level: int | str) -> None:
        """
        Update log level at runtime.

        Usage:
            omni_logger.set_level("DEBUG")
            omni_logger.set_level(logging.WARNING)
        """
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)


class ColorFormatter(logging.Formatter):
    """Premium ANSI colored log formatter for OmniKernal terminal."""

    # Color codes
    GREY = "\x1b[38;20m"
    CYAN = "\x1b[36;20m"
    GREEN = "\x1b[32;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"

    FORMAT_STR = (
        "{asctime} | {level_color}{levelname:<8}{reset} | \x1b[36m[{profile}]\x1b[0m | {message}"
    )

    COLORS = {
        logging.DEBUG: GREY,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: BOLD_RED,
    }

    def __init__(self) -> None:
        super().__init__(style="{", datefmt="%Y-%m-%d %H:%M:%S")

    def format(self, record: logging.LogRecord) -> str:
        # Ensure profile fallback to prevent KeyError
        if not hasattr(record, "profile"):
            record.profile = "system"

        level_color = self.COLORS.get(record.levelno, self.RESET)
        # Build custom formatted string dynamically
        log_fmt = self.FORMAT_STR.format(
            asctime="%(asctime)s",
            level_color=level_color,
            levelname="%(levelname)s",
            reset=self.RESET,
            profile="%(profile)s",
            message="%(message)s",
        )

        formatter = logging.Formatter(log_fmt, datefmt=self.datefmt, style="%")
        return formatter.format(record)


def setup_logger(level: int | str = "INFO", profile_name: str = "default") -> OmniLogger:
    """
    Configures and returns a premium LoggerAdapter for OmniKernal.

    Args:
        level:        Log level — string ("DEBUG", "INFO", "WARNING", "ERROR")
                      or int (logging.DEBUG etc.). Defaults to "INFO".
        profile_name: Context tag shown in log lines. Defaults to "default".

    Usage:
        omni_logger = setup_logger()                    # INFO
        omni_logger = setup_logger(level="DEBUG")       # verbose
        omni_logger = setup_logger(level=logging.WARNING)
    """
    logger = logging.getLogger("omnikernal")
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        handler.setFormatter(ColorFormatter())
        logger.addHandler(handler)
    else:
        # Re-call safe: update existing handlers to the new level
        for handler in logger.handlers:
            handler.setLevel(level)

    return OmniLogger(logger, {"profile": profile_name})


# Global default logger bound to standard typing
omni_logger = setup_logger("DEBUG")
