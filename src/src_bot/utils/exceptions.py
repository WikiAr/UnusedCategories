"""
Custom Exception Hierarchy for Wikipedia Bot Applications.

This module defines a comprehensive exception hierarchy for the Unused
Categories Bot. Using custom exceptions instead of generic ones provides:

- Better error categorization and handling
- More informative error messages
- Easier debugging and logging
- Ability to catch specific error types

The hierarchy is designed with a base BotError exception, with specific
subclasses for different error categories.

Example:
    Handling specific exceptions::

        from utils.exceptions import (
            BotError,
            CredentialError,
            CategoryProcessingError,
        )

        try:
            process_category(category)
        except CategoryProcessingError as e:
            logger.error(f"Failed to process {e.category}: {e}")
        except BotError as e:
            logger.error(f"Bot error: {e}")

    Raising custom exceptions::

        from utils.exceptions import CredentialError

        if not username:
            raise CredentialError("Username not provided")

Notes:
    - All exceptions inherit from BotError for easy catching
    - Each exception includes relevant context in the message
    - Some exceptions store additional attributes for programmatic access

"""

from __future__ import annotations


# =============================================================================
# Base Exception
# =============================================================================


class BotError(Exception):
    """
    Base exception for all bot-related errors.

    This is the root exception class for the bot. All custom exceptions
    inherit from this class, allowing callers to catch all bot errors
    with a single except clause.

    Attributes:
        message: Human-readable error description.
        cause: The underlying exception that caused this error (if any).

    Example:
        >>> try:
        ...     raise BotError("Something went wrong")
        ... except BotError as e:
        ...     print(f"Error: {e}")

    """

    def __init__(
        self,
        message: str,
        cause: Exception | None = None,
    ) -> None:
        """
        Initialize a BotError.

        Args:
            message: Human-readable description of the error.
            cause: Optional underlying exception that caused this error.
                If provided, it will be set as __cause__ for proper
                exception chaining.

        """
        super().__init__(message)
        self.message = message
        self.cause = cause

        if cause is not None:
            self.__cause__ = cause

    def __str__(self) -> str:
        """Return the error message."""
        return self.message


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigurationError(BotError):
    """
    Exception raised for configuration-related errors.

    This exception is raised when there are problems with the bot's
    configuration, such as missing environment variables, invalid
    settings, or missing configuration files.

    Example:
        >>> raise ConfigurationError(
        ...     "Invalid edit throttle value: 'fast'",
        ...     cause=ValueError("not a number")
        ... )

    """



class CredentialError(ConfigurationError):
    """
    Exception raised for credential-related errors.

    This exception is raised when there are problems with authentication
    credentials, such as missing credentials, invalid format, or
    authentication failures.

    Attributes:
        credential_type: The type of credential that had an issue
            (e.g., 'username', 'password', 'token').

    Example:
        >>> raise CredentialError(
        ...     "WIKIPEDIA_BOT_USERNAME environment variable not set"
        ... )

    """

    def __init__(
        self,
        message: str,
        credential_type: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        Initialize a CredentialError.

        Args:
            message: Human-readable description of the error.
            credential_type: The type of credential involved
                (e.g., 'username', 'password').
            cause: Optional underlying exception.

        """
        super().__init__(message, cause)
        self.credential_type = credential_type


# =============================================================================
# API Errors
# =============================================================================


class APIError(BotError):
    """
    Exception raised for Wikipedia API-related errors.

    This exception wraps errors that occur when communicating with the
    MediaWiki API, providing additional context about the failed operation.

    Attributes:
        operation: The API operation that failed (e.g., 'query', 'edit').
        api_code: The error code returned by the API (if available).
        api_info: Additional error information from the API (if available).

    Example:
        >>> raise APIError(
        ...     "Failed to fetch category members",
        ...     operation="query",
        ...     api_code="missingtitle",
        ...     api_info="The specified title does not exist"
        ... )

    """

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        api_code: str | None = None,
        api_info: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        Initialize an APIError.

        Args:
            message: Human-readable description of the error.
            operation: The API operation that failed.
            api_code: The error code from the API response.
            api_info: Additional info from the API response.
            cause: Optional underlying exception.

        """
        super().__init__(message, cause)
        self.operation = operation
        self.api_code = api_code
        self.api_info = api_info

    def __str__(self) -> str:
        """Return a detailed error message."""
        parts = [self.message]
        if self.operation:
            parts.append(f"operation={self.operation}")
        if self.api_code:
            parts.append(f"code={self.api_code}")
        if self.api_info:
            parts.append(f"info={self.api_info}")
        return " | ".join(parts)


class RateLimitError(APIError):
    """
    Exception raised when API rate limits are exceeded.

    This exception indicates that too many requests have been made
    and the bot should wait before retrying.

    Attributes:
        retry_after: Suggested wait time in seconds before retrying.
        limit_type: The type of rate limit that was exceeded.

    Example:
        >>> raise RateLimitError(
        ...     "Rate limit exceeded",
        ...     retry_after=30,
        ...     limit_type="requests"
        ... )

    """

    def __init__(
        self,
        message: str = "API rate limit exceeded",
        retry_after: float | None = None,
        limit_type: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        Initialize a RateLimitError.

        Args:
            message: Human-readable description of the error.
            retry_after: Suggested wait time in seconds.
            limit_type: Type of rate limit (e.g., 'requests', 'edits').
            cause: Optional underlying exception.

        """
        super().__init__(message, operation="rate_limited", cause=cause)
        self.retry_after = retry_after
        self.limit_type = limit_type


class ConnectionError(APIError):
    """
    Exception raised for network connection errors.

    This exception indicates a problem connecting to the Wikipedia API,
    such as network timeouts, DNS failures, or connection refused errors.

    Attributes:
        site_url: The URL that could not be reached.

    Example:
        >>> raise ConnectionError(
        ...     "Failed to connect to ar.wikipedia.org",
        ...     site_url="https://ar.wikipedia.org"
        ... )

    """

    def __init__(
        self,
        message: str = "Failed to connect to Wikipedia API",
        site_url: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        Initialize a ConnectionError.

        Args:
            message: Human-readable description of the error.
            site_url: The URL that could not be reached.
            cause: Optional underlying exception.

        """
        super().__init__(message, operation="connect", cause=cause)
        self.site_url = site_url


# =============================================================================
# Processing Errors
# =============================================================================


class ProcessingError(BotError):
    """
    Base exception for processing-related errors.

    This is the base class for exceptions that occur during the processing
    of categories or pages.

    Attributes:
        item: The item being processed when the error occurred.

    """

    def __init__(
        self,
        message: str,
        item: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        Initialize a ProcessingError.

        Args:
            message: Human-readable description of the error.
            item: The item being processed.
            cause: Optional underlying exception.

        """
        super().__init__(message, cause)
        self.item = item


class CategoryProcessingError(ProcessingError):
    """
    Exception raised when processing a category fails.

    This exception is raised when an error occurs while processing
    a specific category, such as when the category doesn't exist,
    has no interwiki links, or other processing failures.

    Attributes:
        category: The category that failed to process.

    Example:
        >>> raise CategoryProcessingError(
        ...     "No English interwiki link found",
        ...     category="تصنيف:علوم"
        ... )

    """

    def __init__(
        self,
        message: str,
        category: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        Initialize a CategoryProcessingError.

        Args:
            message: Human-readable description of the error.
            category: The category that failed to process.
            cause: Optional underlying exception.

        """
        super().__init__(message, item=category, cause=cause)
        self.category = category

    def __str__(self) -> str:
        """Return an error message including the category name."""
        if self.category:
            return f"[{self.category}] {self.message}"
        return self.message


class PageProcessingError(ProcessingError):
    """
    Exception raised when processing a page fails.

    This exception is raised when an error occurs while processing
    a specific page, such as when fetching content or saving edits.

    Attributes:
        page_title: The title of the page that failed.
        category: The category being processed (if applicable).

    Example:
        >>> raise PageProcessingError(
        ...     "Page is protected",
        ...     page_title="Wikipedia:Main Page",
        ...     category="تصنيف:مقالات"
        ... )

    """

    def __init__(
        self,
        message: str,
        page_title: str | None = None,
        category: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        Initialize a PageProcessingError.

        Args:
            message: Human-readable description of the error.
            page_title: The title of the page that failed.
            category: The category being processed.
            cause: Optional underlying exception.

        """
        super().__init__(message, item=page_title, cause=cause)
        self.page_title = page_title
        self.category = category

    def __str__(self) -> str:
        """Return an error message including the page title."""
        parts = []
        if self.category:
            parts.append(f"[{self.category}]")
        if self.page_title:
            parts.append(f"Page: {self.page_title}")
        parts.append(self.message)
        return " | ".join(parts)


class EditError(ProcessingError):
    """
    Exception raised when an edit operation fails.

    This exception is raised when saving changes to a page fails,
    such as when the page is protected, there's an edit conflict,
    or the user doesn't have permission.

    Attributes:
        page_title: The title of the page that couldn't be edited.
        edit_summary: The edit summary that was attempted.

    Example:
        >>> raise EditError(
        ...     "Edit conflict detected",
        ...     page_title="Test Page",
        ...     edit_summary="Bot: Adding category"
        ... )

    """

    def __init__(
        self,
        message: str,
        page_title: str | None = None,
        edit_summary: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        Initialize an EditError.

        Args:
            message: Human-readable description of the error.
            page_title: The title of the page.
            edit_summary: The attempted edit summary.
            cause: Optional underlying exception.

        """
        super().__init__(message, item=page_title, cause=cause)
        self.page_title = page_title
        self.edit_summary = edit_summary


# =============================================================================
# Validation Errors
# =============================================================================


class ValidationError(BotError):
    """
    Exception raised for validation errors.

    This exception is raised when input validation fails, such as
    invalid category names, malformed titles, or other input issues.

    Attributes:
        field: The field that failed validation.
        value: The invalid value (if safe to include).

    Example:
        >>> raise ValidationError(
        ...     "Category name cannot be empty",
        ...     field="category_name",
        ...     value=""
        ... )

    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        Initialize a ValidationError.

        Args:
            message: Human-readable description of the error.
            field: The field that failed validation.
            value: The invalid value (avoid including sensitive data).
            cause: Optional underlying exception.

        """
        super().__init__(message, cause)
        self.field = field
        self.value = value


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Base exception
    "BotError",
    # Configuration errors
    "ConfigurationError",
    "CredentialError",
    # API errors
    "APIError",
    "RateLimitError",
    "ConnectionError",
    # Processing errors
    "ProcessingError",
    "CategoryProcessingError",
    "PageProcessingError",
    "EditError",
    # Validation errors
    "ValidationError",
]
