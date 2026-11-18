"""
Logging configuration with colored output.

Handlers and their levels:
    - console   -> `level` (default DEBUG: everything)
    - <name>.log          -> `file_level` (default INFO: INFO/WARNING/ERROR/CRITICAL)
    - <name>_errors.log   -> `error_level` (default ERROR: ERROR/CRITICAL only)
"""

from __future__ import annotations

import functools
import logging
import os
import re
import sys
from logging.handlers import TimedRotatingFileHandler, WatchedFileHandler
from pathlib import Path
from typing import Any

import colorlog


@functools.lru_cache(maxsize=1)
def get_color_table() -> dict[str, str]:
    """Build a mapping of color names to ANSI templates."""
    # new Define the color codes for different colors
    color_numbers = {
        "red": 91,
        "green": 92,
        "yellow": 93,
        "blue": 94,
        "purple": 95,
        "cyan": 96,
        "white": 97,
        "black": 98,
        "grey": 99,
        "gray": 100,
        "underline": 4,
        "invert": 7,
        "blink": 5,
        "lightblack": 108,
        "bold": 1,
    }
    data: dict[str, Any] = {x: f"\033[{v}m%s\033[00m" for x, v in color_numbers.items()}

    # Add light versions of the colors to the color table
    for color in ["purple", "yellow", "blue", "red", "green", "cyan", "gray"]:
        data[f"light{color}"] = data.get(color, 0)

    # Add some additional color names to the color table
    data["aqua"] = data.get("cyan", 0)
    data["lightaqua"] = data.get("cyan", 0)
    data["lightgrey"] = data.get("gray", 0)
    data["grey"] = data.get("gray", 0)
    data["lightwhite"] = data.get("gray", 0)
    data["light"] = 0

    return data


def format_colored_text(textm: str | Any) -> str:
    """
    Prints the given text with color formatting.

    The text can contain color tags like '<<color>>' where 'color' is the name of the color.
    The color will be applied to the text that follows the tag, until the end of the string or until a '<<default>>' tag is found.

    :param textm: The text to print. Can contain color tags.
    """
    # If the input is not a string, print it as is and return
    if not isinstance(textm, str):
        return textm

    color_table = get_color_table()
    # Define a pattern for color tags
    _color_pat = r"((:?\w+|previous);?(:?\w+|previous)?)"
    # Compile a regex for color tags
    colorTagR = re.compile(rf"(?:\03{{|<<){_color_pat}(?:}}|>>)")

    # Initialize a stack for color tags
    color_stack = ["default"]

    # If the text does not contain any color tags, print it as is and return
    if "\03" not in textm and "<<" not in textm:
        return textm

    # Split the text into parts based on the color tags
    text_parts = colorTagR.split(textm) + ["default"]

    # Enumerate the parts for processing
    enu = enumerate(zip(text_parts[::4], text_parts[1::4], strict=False))

    # Initialize the string to be printed
    toprint = ""

    # Process each part of the text
    for _, (text, next_color) in enu:
        # Get the current color from the color stack
        # print(f"i: {index}, {text=}, {next_color=}")
        current_color = color_stack[-1]

        # If the next color is 'previous', pop the color stack to get the previous color
        if next_color == "previous":
            if len(color_stack) > 1:  # keep the last element in the stack
                color_stack.pop()
            next_color = color_stack[-1]
        else:
            # If the next color is not 'previous', add it to the color stack
            color_stack.append(next_color)

        # Get the color code for the current color
        cc = color_table.get(current_color, "")

        # If the color code is not empty, apply it to the text
        if cc:
            text = cc % text

        # Add the colored text to the string to be printed
        toprint += text

    # Print the final colored text
    return toprint


def wrap_color_messages(format_message):
    """Wrap the color messages to include additional context."""

    def wrapper(record):
        # Add custom attributes or modify the record as needed
        return format_colored_text(format_message(record))

    return wrapper

def _daily_log_namer(default_name: str) -> str:
    """Rename rotated log from 'errors.log.2024-01-15' to 'errors.2024-01-15.log'."""
    directory = os.path.dirname(default_name)
    basename = os.path.basename(default_name)
    # default format: "<stem>.log.YYYY-MM-DD"
    parts = basename.rsplit(".", 1)
    if len(parts) == 2:
        date_part = parts[1]
        stem = Path(parts[0]).stem  # 'errors.log' -> 'errors'
        return os.path.join(directory, f"{stem}.{date_part}.log")
    return default_name


def _to_level(value: str | int, default: int = logging.INFO) -> int:
    """Convert a level name or number to a numeric logging level."""
    if isinstance(value, str):
        return getattr(logging, value.upper(), default)
    return value


def prepare_log_file(
    log_file: str | None,
    project_logger: logging.Logger,
) -> Path | None:
    """
    Prepare the log file path and create parent directories if needed.
    """
    if not log_file:
        return None
    log_file_path = os.path.expandvars(str(log_file))
    log_file_path = Path(log_file_path).expanduser()

    try:
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        project_logger.error("Failed to create log directory: %s", e)
        log_file_path = None
    return log_file_path


def setup_file_handler(
    project_logger: logging.Logger,
    log_file: Path,
    level: int,
    daily_rotation: bool = False,
) -> None:
    """
    Attach a file handler to the logger, optionally rotating daily at midnight (UTC).
    """
    file_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)-8s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    if daily_rotation:
        file_handler = TimedRotatingFileHandler(
            log_file,
            when="midnight",
            interval=1,
            backupCount=90,
            encoding="utf-8",
            utc=True,
        )
        file_handler.namer = _daily_log_namer
    else:
        file_handler = WatchedFileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(level)
    project_logger.addHandler(file_handler)


def setup_logging(
    level: str | int = "DEBUG",  # console level
    name: str = __name__,
    log_file: str | None = None,
    error_log_file: str | None = None,
    use_colorlog: None | bool = None,
    daily_rotation: bool = False,
    file_level: str | int = "INFO",  # app.log level
    error_level: str | int = "ERROR",  # errors.log level
) -> None:
    """
    Configure logging for the project namespace only.

    Args:
        level: console handler level.
        file_level: main log file level.
        error_level: error log file level.
    """
    project_logger = logging.getLogger(name)

    if project_logger.handlers:
        return

    if use_colorlog is None:
        use_colorlog = sys.stderr.isatty()

    console_level = _to_level(level)
    app_file_level = _to_level(file_level)
    errors_file_level = _to_level(error_level, default=logging.ERROR)

    # The logger itself must let everything through;
    # each handler then filters by its own level.
    project_logger.setLevel(min(console_level, app_file_level, errors_file_level))
    project_logger.propagate = False

    fmt = "%(asctime)s - %(name)s - %(log_color)s%(levelname)-s %(reset)s- [%(funcName)s:%(lineno)d] - %(message)s"
    if use_colorlog:
        console_formatter = colorlog.ColoredFormatter(
            # Standard format: Time - Name - Level - [Func:Line] - Message
            fmt=fmt,
            datefmt="%H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        )
        # message colorizer
        console_formatter.formatMessage = wrap_color_messages(console_formatter.formatMessage)
    else:
        console_formatter = logging.Formatter(
            # Standard format: Time - Name - Level - [Func:Line] - Message
            fmt="%(asctime)s - %(name)s - %(levelname)-s - [%(funcName)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(console_level)
    project_logger.addHandler(console_handler)

    project_logger.debug("Setting up logging for '%s' with level '%s'", name, level)

    if log_file:
        log_file_path = prepare_log_file(log_file, project_logger)
        if log_file_path:
            setup_file_handler(
                project_logger,
                log_file_path,
                app_file_level,
                daily_rotation=daily_rotation,
            )

    if error_log_file:
        error_log_file_path = prepare_log_file(error_log_file, project_logger)
        if error_log_file_path:
            setup_file_handler(
                project_logger,
                error_log_file_path,
                errors_file_level,
                daily_rotation=daily_rotation,
            )


__all__ = [
    "setup_logging",
]
