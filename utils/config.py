"""
Configuration Management for Wikipedia Bot Applications.

This module provides configuration management for the Unused Categories Bot,
replacing global state with a clean, encapsulated configuration class.

The module includes:
- BotConfig: Main configuration class with all bot settings
- Configuration loading from environment variables
- Validation of configuration values
- Edit approval workflow management

Example:
    Basic usage::

        from utils.config import BotConfig

        # Create config with defaults
        config = BotConfig()

        # Enable interactive mode
        config.ask_mode = True

        # Check approval for an edit
        if config.request_approval("Test Page", "old", "new"):
            page.save(new_text, summary="Bot edit")

    Loading from environment::

        from utils.config import load_config_from_env

        config = load_config_from_env()
        print(f"Category limit: {config.category_limit}")

Notes:
    - Configuration is immutable after creation unless explicitly modified
    - Environment variables override defaults
    - All settings have sensible defaults

"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Optional

from .exceptions import ConfigurationError, CredentialError
from .log import logger


# =============================================================================
# Constants
# =============================================================================

# Default configuration values
DEFAULT_CATEGORY_LIMIT: int = 1000
DEFAULT_EDIT_SUMMARY: str = "بوت: أضاف 1 تصنيف"
DEFAULT_RATE_LIMIT: float = 10.0  # calls per second
DEFAULT_MAX_EDITS_PER_RUN: int = 0  # 0 = unlimited

# Environment variable names
ENV_BOT_USERNAME: str = "WIKI_BOT_USERNAME"
ENV_BOT_PASSWORD: str = "WIKI_BOT_PASSWORD"
ENV_CATEGORY_LIMIT: str = "WIKI_BOT_CATEGORY_LIMIT"
ENV_RATE_LIMIT: str = "WIKI_BOT_RATE_LIMIT"
ENV_ASK_MODE: str = "WIKI_BOT_ASK_MODE"
ENV_DRY_RUN: str = "WIKI_BOT_DRY_RUN"


# =============================================================================
# Enums
# =============================================================================

class ApprovalDecision(Enum):
    """
    Possible decisions from edit approval workflow.

    Attributes:
        APPROVE: Approve this specific edit.
        REJECT: Reject this specific edit.
        APPROVE_ALL: Approve this and all remaining edits.
        ABORT: Stop processing entirely.

    """
    APPROVE = auto()
    REJECT = auto()
    APPROVE_ALL = auto()
    ABORT = auto()


class LogLevel(Enum):
    """
    Log level options for the bot.

    Maps to Python logging module levels.

    """
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Credentials:
    """
    Wikipedia bot credentials.

    Stores username and password for Wikipedia API authentication.
    Credentials should be loaded from environment variables or a
    secure configuration source.

    Attributes:
        username: The bot account username.
        password: The bot account password.

    Example:
        >>> creds = Credentials("MyBot", "secret123")
        >>> site.login(creds.username, creds.password)

    Security Note:
        Never hardcode credentials in source code. Always load from
        environment variables or a secure credential store.

    """

    username: str
    password: str

    def __post_init__(self) -> None:
        """Validate credentials after initialization."""
        if not self.username:
            raise CredentialError(
                "Username cannot be empty",
                credential_type="username"
            )
        if not self.password:
            raise CredentialError(
                "Password cannot be empty",
                credential_type="password"
            )

    @classmethod
    def from_env(cls) -> "Credentials":
        """
        Load credentials from environment variables.

        Returns:
            A Credentials instance populated from WIKI_BOT_USERNAME
            and WIKI_BOT_PASSWORD environment variables.

        Raises:
            CredentialError: If either environment variable is not set.

        Example:
            >>> # Set environment variables first
            >>> # os.environ["WIKI_BOT_USERNAME"] = "MyBot"
            >>> # os.environ["WIKI_BOT_PASSWORD"] = "secret"
            >>> creds = Credentials.from_env()

        """
        username = os.environ.get(ENV_BOT_USERNAME)
        password = os.environ.get(ENV_BOT_PASSWORD)

        if not username:
            raise CredentialError(
                f"{ENV_BOT_USERNAME} environment variable not set",
                credential_type="username"
            )
        if not password:
            raise CredentialError(
                f"{ENV_BOT_PASSWORD} environment variable not set",
                credential_type="password"
            )

        return cls(username=username, password=password)

    def __repr__(self) -> str:
        """Return a safe string representation (hides password)."""
        return f"Credentials(username='{self.username}', password='***')"


@dataclass
class BotConfig:
    """
    Configuration for the Unused Categories Bot.

    This class encapsulates all configuration options for the bot,
    replacing the previous global state pattern. It provides:

    - Immutable configuration after initialization
    - Type-safe configuration values
    - Environment variable integration
    - Edit approval workflow management

    Attributes:
        ask_mode: If True, prompt for approval before each edit.
        auto_approve_all: If True, approve all edits without prompting.
        dry_run: If True, don't make actual edits (simulation mode).
        category_limit: Maximum number of categories to process.
        edit_summary: Default edit summary for bot edits.
        rate_limit: Maximum API calls per second.
        max_edits_per_run: Maximum edits per run (0 = unlimited).
        log_level: Logging verbosity level.
        credentials: Wikipedia API credentials (optional).

    Example:
        >>> config = BotConfig(ask_mode=True, category_limit=100)
        >>> if config.should_request_approval():
        ...     decision = config.request_approval("Page", "old", "new")
        ...     if decision == ApprovalDecision.APPROVE:
        ...         make_edit()

    """

    # Interactive mode settings
    ask_mode: bool = False
    auto_approve_all: bool = False

    # Execution settings
    dry_run: bool = False
    category_limit: int = DEFAULT_CATEGORY_LIMIT
    max_edits_per_run: int = DEFAULT_MAX_EDITS_PER_RUN

    # Edit settings
    edit_summary: str = DEFAULT_EDIT_SUMMARY

    # Rate limiting
    rate_limit: float = DEFAULT_RATE_LIMIT

    # Logging
    log_level: LogLevel = LogLevel.INFO

    # Credentials (loaded separately)
    credentials: Optional[Credentials] = None

    # Internal state
    _edits_made: int = field(default=0, init=False, repr=False)
    _approval_handler: Optional[Callable[[str, str, str], ApprovalDecision]] = field(
        default=None, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.category_limit < 0:
            raise ConfigurationError(
                f"category_limit must be non-negative, got {self.category_limit}"
            )
        if self.rate_limit <= 0:
            raise ConfigurationError(
                f"rate_limit must be positive, got {self.rate_limit}"
            )
        if self.max_edits_per_run < 0:
            raise ConfigurationError(
                f"max_edits_per_run must be non-negative, got {self.max_edits_per_run}"
            )

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def edits_made(self) -> int:
        """Get the number of edits made in this run."""
        return self._edits_made

    @property
    def edits_remaining(self) -> Optional[int]:
        """
        Get the number of edits remaining, or None if unlimited.

        Returns:
            Number of edits remaining, or None if max_edits_per_run is 0.

        """
        if self.max_edits_per_run == 0:
            return None
        return max(0, self.max_edits_per_run - self._edits_made)

    @property
    def can_edit(self) -> bool:
        """Check if more edits are allowed."""
        if self.max_edits_per_run == 0:
            return True
        return self._edits_made < self.max_edits_per_run

    # -------------------------------------------------------------------------
    # Edit Tracking
    # -------------------------------------------------------------------------

    def record_edit(self) -> None:
        """Record that an edit was made."""
        self._edits_made += 1

    def reset_edit_count(self) -> None:
        """Reset the edit counter."""
        self._edits_made = 0

    # -------------------------------------------------------------------------
    # Approval Workflow
    # -------------------------------------------------------------------------

    def set_approval_handler(
        self,
        handler: Callable[[str, str, str], ApprovalDecision]
    ) -> None:
        """
        Set a custom approval handler function.

        The handler will be called for each edit when ask_mode is enabled.
        It receives (page_title, old_text, new_text) and should return
        an ApprovalDecision.

        Args:
            handler: A function that takes (page_title, old_text, new_text)
                and returns an ApprovalDecision.

        Example:
            >>> def my_handler(page: str, old: str, new: str) -> ApprovalDecision:
            ...     print(f"Edit {page}?")
            ...     response = input("[y/n/a]: ")
            ...     if response == 'a':
            ...         return ApprovalDecision.APPROVE_ALL
            ...     return ApprovalDecision.APPROVE if response == 'y' else ApprovalDecision.REJECT
            >>> config.set_approval_handler(my_handler)

        """
        self._approval_handler = handler

    def should_request_approval(self) -> bool:
        """
        Check if approval should be requested for the next edit.

        Returns:
            True if approval should be requested, False otherwise.

        """
        if self.auto_approve_all:
            return False
        return self.ask_mode

    def request_approval(
        self,
        page_title: str,
        old_text: str,
        new_text: str,
    ) -> ApprovalDecision:
        """
        Request approval for an edit.

        This method handles the approval workflow:
        1. If auto_approve_all is True, returns APPROVE
        2. If ask_mode is False, returns APPROVE
        3. Otherwise, calls the approval handler or prompts interactively

        Args:
            page_title: Title of the page being edited.
            old_text: Current text of the page.
            new_text: Proposed new text for the page.

        Returns:
            An ApprovalDecision indicating how to proceed.

        Example:
            >>> decision = config.request_approval("Test", "old", "new")
            >>> if decision == ApprovalDecision.APPROVE:
            ...     page.save(new_text, summary=config.edit_summary)
            >>> elif decision == ApprovalDecision.APPROVE_ALL:
            ...     config.auto_approve_all = True
            ...     page.save(new_text, summary=config.edit_summary)

        """
        # Auto-approve is enabled
        if self.auto_approve_all:
            return ApprovalDecision.APPROVE

        # Not in ask mode - approve automatically
        if not self.ask_mode:
            return ApprovalDecision.APPROVE

        # Use custom handler if set
        if self._approval_handler is not None:
            decision = self._approval_handler(page_title, old_text, new_text)
            if decision == ApprovalDecision.APPROVE_ALL:
                self.auto_approve_all = True
            return decision

        # Default interactive prompt
        return self._interactive_prompt(page_title, old_text, new_text)

    def _interactive_prompt(
        self,
        page_title: str,
        old_text: str,
        new_text: str,
    ) -> ApprovalDecision:
        """
        Show an interactive approval prompt.

        Args:
            page_title: Title of the page.
            old_text: Current text.
            new_text: Proposed new text.

        Returns:
            The user's decision.

        """
        from .diff import showDiff

        logger.info(f"\n{'='*60}")
        logger.info(f"Target: {page_title}")
        logger.info(f"{'='*60}")

        # Show the diff
        showDiff(old_text, new_text)
        logger.info(f"{'='*60}")

        logger.info(
            f"<<green>> Target: {page_title}, "
            f"Options: [y]es / [n]o / [a]ll (approve all remaining)"
        )

        try:
            response = input("Confirm edit? [Y/n/a]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            logger.warning("Input interrupted, rejecting edit.")
            return ApprovalDecision.REJECT

        if response in ('', 'y', 'yes'):
            return ApprovalDecision.APPROVE

        if response == 'a':
            self.auto_approve_all = True
            logger.info("Auto-approving all remaining edits.")
            return ApprovalDecision.APPROVE

        logger.error_red("Edit rejected.")
        return ApprovalDecision.REJECT

    # -------------------------------------------------------------------------
    # Factory Methods
    # -------------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> "BotConfig":
        """
        Create a BotConfig from environment variables.

        Reads the following environment variables:
        - WIKI_BOT_ASK_MODE: Set to 'true' to enable interactive mode
        - WIKI_BOT_DRY_RUN: Set to 'true' for simulation mode
        - WIKI_BOT_CATEGORY_LIMIT: Maximum categories to process
        - WIKI_BOT_RATE_LIMIT: API calls per second

        Returns:
            A BotConfig instance with values from environment.

        Example:
            >>> # In shell:
            >>> # export WIKI_BOT_ASK_MODE=true
            >>> # export WIKI_BOT_CATEGORY_LIMIT=100
            >>> config = BotConfig.from_env()

        """
        # Parse boolean settings
        ask_mode = os.environ.get(ENV_ASK_MODE, '').lower() in ('true', '1', 'yes')
        dry_run = os.environ.get(ENV_DRY_RUN, '').lower() in ('true', '1', 'yes')

        # Parse numeric settings
        category_limit = DEFAULT_CATEGORY_LIMIT
        if ENV_CATEGORY_LIMIT in os.environ:
            try:
                category_limit = int(os.environ[ENV_CATEGORY_LIMIT])
            except ValueError:
                logger.warning(
                    f"Invalid {ENV_CATEGORY_LIMIT}: {os.environ[ENV_CATEGORY_LIMIT]}"
                )

        rate_limit = DEFAULT_RATE_LIMIT
        if ENV_RATE_LIMIT in os.environ:
            try:
                rate_limit = float(os.environ[ENV_RATE_LIMIT])
            except ValueError:
                logger.warning(
                    f"Invalid {ENV_RATE_LIMIT}: {os.environ[ENV_RATE_LIMIT]}"
                )

        # Load credentials
        credentials = None
        try:
            credentials = Credentials.from_env()
        except CredentialError:
            pass  # Credentials can be loaded later

        return cls(
            ask_mode=ask_mode,
            dry_run=dry_run,
            category_limit=category_limit,
            rate_limit=rate_limit,
            credentials=credentials,
        )

    @classmethod
    def for_interactive(cls) -> "BotConfig":
        """
        Create a config for interactive use.

        This preset enables ask mode and sets a low category limit
        for safe manual operation.

        Returns:
            A BotConfig configured for interactive use.

        """
        return cls(
            ask_mode=True,
            category_limit=10,
            log_level=LogLevel.DEBUG,
        )

    @classmethod
    def for_production(cls) -> "BotConfig":
        """
        Create a config for production use.

        This preset disables ask mode and sets higher limits for
        automated batch processing.

        Returns:
            A BotConfig configured for production use.

        """
        return cls(
            ask_mode=False,
            category_limit=DEFAULT_CATEGORY_LIMIT,
            rate_limit=10.0,
            log_level=LogLevel.INFO,
        )

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the config to a dictionary.

        Returns:
            A dictionary representation of the configuration.
            Credentials are excluded for security.

        """
        return {
            "ask_mode": self.ask_mode,
            "auto_approve_all": self.auto_approve_all,
            "dry_run": self.dry_run,
            "category_limit": self.category_limit,
            "edit_summary": self.edit_summary,
            "rate_limit": self.rate_limit,
            "max_edits_per_run": self.max_edits_per_run,
            "log_level": self.log_level.name,
            "edits_made": self._edits_made,
            "has_credentials": self.credentials is not None,
        }

    def __str__(self) -> str:
        """Return a string representation of the configuration."""
        return (
            f"BotConfig(ask_mode={self.ask_mode}, "
            f"dry_run={self.dry_run}, "
            f"category_limit={self.category_limit}, "
            f"rate_limit={self.rate_limit})"
        )


# =============================================================================
# Module-level default config (for backwards compatibility)
# =============================================================================

def get_default_config() -> BotConfig:
    """
    Get the default configuration.

    This function creates a new BotConfig instance with default values.
    For backwards compatibility with code that used global state.

    Returns:
        A new BotConfig with default settings.

    """
    return BotConfig()


# =============================================================================
# Convenience function
# =============================================================================

def load_config_from_env() -> BotConfig:
    """
    Load configuration from environment variables.

    This is a convenience wrapper around BotConfig.from_env().

    Returns:
        A BotConfig instance loaded from environment variables.

    """
    return BotConfig.from_env()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Constants
    "DEFAULT_CATEGORY_LIMIT",
    "DEFAULT_EDIT_SUMMARY",
    "DEFAULT_RATE_LIMIT",
    "DEFAULT_MAX_EDITS_PER_RUN",
    # Enums
    "ApprovalDecision",
    "LogLevel",
    # Classes
    "Credentials",
    "BotConfig",
    # Functions
    "get_default_config",
    "load_config_from_env",
]
