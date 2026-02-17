"""
Colorized Logging Utilities for Wikipedia Bot Applications.

This module provides a custom logger wrapper that supports colorized output
using ANSI escape codes. It wraps Python's standard logging module with
additional functionality for terminal color formatting.

The color formatting uses a custom syntax where colors are specified using
`<<color>>` tags in the message string. For example:
    - `<<green>>Success message<<default>>`
    - `<<red>>Error: something failed<<default>>`

Supported colors include: red, green, yellow, blue, purple, cyan, white,
black, grey, gray, and their light variants (e.g., lightgreen, lightblue).

Example:
    Basic usage::

        from utils.log import logger

        logger.set_level("INFO")
        logger.info("<<green>>Operation successful<<default>>")
        logger.error_red("Something went wrong")

    Creating a new logger instance::

        from utils.log import LoggerWrap
        my_logger = LoggerWrap("my_module", level=logging.DEBUG)
        my_logger.debug("Debug message")

Attributes:
    logger: A default LoggerWrap instance configured for the current module.

Notes:
    - Color codes only work on terminals that support ANSI escape codes
    - On Windows, you may need to enable ANSI support or use Windows Terminal
    - Colors are applied by the make_str() function from the diff module

"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .diff import make_str, showDiff

if TYPE_CHECKING:
    from typing import Union


class LoggerWrap:
    """
    A wrapper around Python's logging.Logger with color support.

    This class provides a project-scoped logger with additional helpers for
    colorized output. It wraps the standard logging.Logger and adds methods
    for applying color formatting to log messages.

    Attributes:
        _logger: The underlying logging.Logger instance.

    Example:
        >>> logger = LoggerWrap("my_app", level=logging.INFO)
        >>> logger.info("<<green>>Hello, World!<<default>>")
        >>> logger.error_red("An error occurred")

    Note:
        The logger is initialized with propagate=False to prevent messages
        from being passed to the root logger, which avoids duplicate output.

    """

    def __init__(
        self,
        name: str,
        disable_log: bool = False,
        level: int = logging.ERROR,
    ) -> None:
        """
        Initialize a new LoggerWrap instance.

        Creates a wrapped logger with optional output disabling. If the logger
        already has handlers (e.g., from a previous initialization), no new
        handlers are added to prevent duplicate output.

        Args:
            name: The name for the logger, typically __name__ of the calling
                module. This name is used to identify the logger in the
                logging hierarchy.
            disable_log: If True, the logger is completely disabled and will
                not produce any output. Defaults to False.
            level: The initial logging level. Only messages at this level or
                higher will be output. Defaults to logging.ERROR.
                Common levels:
                - logging.DEBUG (10): Detailed diagnostic information
                - logging.INFO (20): Confirmation of expected operation
                - logging.WARNING (30): Indication of potential problems
                - logging.ERROR (40): Serious problems that prevented operation
                - logging.CRITICAL (50): Severe errors causing program exit

        Example:
            >>> logger = LoggerWrap(__name__, level=logging.INFO)
            >>> logger.info("Logger initialized")

        """
        self._logger = logging.getLogger(name)

        # Prevent leaking to root logger to avoid duplicate messages
        self._logger.propagate = False

        if disable_log:
            self._logger.disabled = True
            return

        # Only add handlers if none exist (prevents duplicate handlers)
        if not self._logger.handlers:
            self._logger.setLevel(level)

            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)

            self._logger.addHandler(handler)

    def set_level(self, level: Union[int, str]) -> None:
        """
        Set the logging level for the underlying logger.

        This method allows changing the logging level at runtime. Messages
        below this level will not be output.

        Args:
            level: The logging level to set. Can be either:
                - An integer level (e.g., logging.INFO, logging.DEBUG)
                - A string level name (e.g., "INFO", "DEBUG", "WARNING")

        Example:
            >>> logger.set_level(logging.DEBUG)
            >>> logger.set_level("INFO")

        """
        self._logger.setLevel(level)

    def setLevel(self, level: Union[int, str]) -> None:
        """
        Alias for set_level() for compatibility with standard logging API.

        This method provides compatibility with code expecting the standard
        logging.Logger.setLevel() method signature.

        Args:
            level: The logging level to set (int or string).

        """
        return self.set_level(level)

    def disable_logger(self, is_disabled: bool) -> None:
        """
        Enable or disable the underlying logger dynamically.

        When disabled, the logger will not produce any output regardless of
        the logging level. This is useful for temporarily suppressing output.

        Args:
            is_disabled: True to disable the logger, False to enable it.

        Example:
            >>> logger.disable_logger(True)   # Suppress all output
            >>> logger.disable_logger(False)  # Re-enable output

        """
        self._logger.disabled = is_disabled

    def logger(self) -> logging.Logger:
        """
        Get access to the raw logging.Logger instance.

        This method exposes the underlying logger for advanced use cases
        where direct access to the standard logger is needed.

        Returns:
            The underlying logging.Logger instance.

        Example:
            >>> raw_logger = logger.logger()
            >>> raw_logger.log(logging.INFO, "Custom log message")

        """
        return self._logger

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
        Log a debug message after formatting color codes.

        Debug messages are for detailed diagnostic information, typically
        only of interest when diagnosing problems.

        Args:
            msg: The message string, which may contain color tags like
                <<green>> or <<red>>.
            *args: Additional positional arguments passed to the logger.
            **kwargs: Additional keyword arguments passed to the logger.

        """
        self._logger.debug(make_str(msg), *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
        Log an info message after formatting color codes.

        Info messages confirm that things are working as expected.

        Args:
            msg: The message string, which may contain color tags.
            *args: Additional positional arguments passed to the logger.
            **kwargs: Additional keyword arguments passed to the logger.

        """
        self._logger.info(make_str(msg), *args, **kwargs)

    def info_if_or_debug(self, msg: str, value: Any) -> None:
        """
        Log an info message if value is truthy, otherwise log a debug message.

        This is a convenience method for conditional logging based on a
        condition value.

        Args:
            msg: The message string to log, which may contain color tags.
            value: A condition value. If truthy, logs at INFO level;
                otherwise logs at DEBUG level. The value itself is not
                logged, only used as a condition.

        Example:
            >>> logger.info_if_or_debug("<<green>>Success<<default>>", result)
            # Logs at INFO if result is truthy, DEBUG otherwise

        """
        if value:
            self._logger.info(make_str(msg))
        else:
            self._logger.debug(make_str(msg))

    def output(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
        Alias for info logging while preserving color formatting.

        This method provides a more intuitive name for outputting messages
        at the INFO level.

        Args:
            msg: The message string, which may contain color tags.
            *args: Additional positional arguments passed to the logger.
            **kwargs: Additional keyword arguments passed to the logger.

        """
        self._logger.info(make_str(msg), *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
        Log a warning message with formatted content.

        Warning messages indicate a potential problem that doesn't prevent
        the program from working but should be addressed.

        Args:
            msg: The message string, which may contain color tags.
            *args: Additional positional arguments passed to the logger.
            **kwargs: Additional keyword arguments passed to the logger.

        """
        self._logger.warning(make_str(msg), *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
        Log an error message with formatted content.

        Error messages indicate a more serious problem that prevented
        an operation from completing.

        Args:
            msg: The message string, which may contain color tags.
            *args: Additional positional arguments passed to the logger.
            **kwargs: Additional keyword arguments passed to the logger.

        """
        self._logger.error(make_str(msg), *args, **kwargs)

    def error_red(self, msg: str) -> None:
        """
        Log an error message with forced red coloring.

        This is a convenience method that wraps the message in red color
        tags, ensuring the output is highlighted in red on compatible
        terminals.

        Args:
            msg: The error message to log. Will be wrapped in <<red>>
                and <<default>> tags automatically.

        Example:
            >>> logger.error_red("Database connection failed")

        """
        text = f"<<red>> {str(msg)} <<default>>"
        self._logger.error(make_str(text))

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
        Log a critical message with formatted content.

        Critical messages indicate a severe error that may cause the
        program to terminate.

        Args:
            msg: The message string, which may contain color tags.
            *args: Additional positional arguments passed to the logger.
            **kwargs: Additional keyword arguments passed to the logger.

        """
        self._logger.critical(make_str(msg), *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
        Log an exception with traceback using formatted content.

        This method logs an error message and includes the exception
        traceback. It should only be called from within an exception handler.

        Args:
            msg: The message string describing the exception context.
            *args: Additional positional arguments passed to the logger.
            **kwargs: Additional keyword arguments passed to the logger.

        Example:
            >>> try:
            ...     risky_operation()
            ... except Exception:
            ...     logger.exception("Operation failed")

        """
        self._logger.exception(make_str(msg), *args, **kwargs)

    def log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        """
        Log at an arbitrary level with formatted content.

        This method allows logging at any specified level.

        Args:
            level: The logging level (integer, e.g., logging.INFO).
            msg: The message string, which may contain color tags.
            *args: Additional positional arguments passed to the logger.
            **kwargs: Additional keyword arguments passed to the logger.

        """
        self._logger.log(level, make_str(msg), *args, **kwargs)

    def showDiff(self, oldtext: str, newtext: str) -> None:
        """
        Display a colorized diff between two text strings.

        This method shows the differences between old and new text using
        color highlighting to indicate additions and deletions.

        Args:
            oldtext: The original text string.
            newtext: The modified text string.

        Example:
            >>> logger.showDiff("Hello World", "Hello Python")
            # Shows a diff with "World" in red and "Python" in green

        """
        showDiff(oldtext, newtext)


# Default logger instance for the module
logger = LoggerWrap(__name__)


__all__ = [
    "logger",
    "LoggerWrap",
]
