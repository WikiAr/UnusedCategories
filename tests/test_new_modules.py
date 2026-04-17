#!/usr/bin/env python3
"""
Comprehensive tests for the utils package modules.

This test module covers:
- Configuration (BotConfig, Credentials)
- Exceptions hierarchy
- Rate limiting
- Type definitions

"""

import os
import pytest
import time
from unittest.mock import patch, MagicMock
from typing import Any

from src.utils.config import (
    BotConfig,
    Credentials,
    ApprovalDecision,
    LogLevel,
    DEFAULT_CATEGORY_LIMIT,
    DEFAULT_EDIT_SUMMARY,
    DEFAULT_RATE_LIMIT,
)
from src.utils.exceptions import (
    BotError,
    ConfigurationError,
    CredentialError,
    APIError,
    RateLimitError,
    CategoryProcessingError,
    PageProcessingError,
    EditError,
    ValidationError,
)
from src.utils.rate_limiter import (
    SimpleRateLimiter,
    TokenBucketRateLimiter,
    AdaptiveRateLimiter,
    create_rate_limiter,
)
from src.utils.types import (
    is_valid_page,
    is_valid_site,
)


# =============================================================================
# Configuration Tests
# =============================================================================

class TestCredentials:
    """Tests for the Credentials class."""

    def test_credentials_creation(self) -> None:
        """Test creating credentials with valid data."""
        creds = Credentials(username="test_user", password="test_pass")
        assert creds.username == "test_user"
        assert creds.password == "test_pass"

    def test_credentials_empty_username_raises(self) -> None:
        """Test that empty username raises CredentialError."""
        with pytest.raises(CredentialError, match="Username cannot be empty"):
            Credentials(username="", password="test_pass")

    def test_credentials_empty_password_raises(self) -> None:
        """Test that empty password raises CredentialError."""
        with pytest.raises(CredentialError, match="Password cannot be empty"):
            Credentials(username="test_user", password="")

    def test_credentials_repr_hides_password(self) -> None:
        """Test that repr hides the password."""
        creds = Credentials(username="test_user", password="secret123")
        repr_str = repr(creds)
        assert "test_user" in repr_str
        assert "secret123" not in repr_str
        assert "***" in repr_str

    @patch.dict(os.environ, {
        "WIKIPEDIA_BOT_USERNAME": "env_user",
        "WIKIPEDIA_BOT_PASSWORD": "env_pass"
    })
    def test_credentials_from_env(self) -> None:
        """Test loading credentials from environment variables."""
        creds = Credentials.from_env()
        assert creds.username == "env_user"
        assert creds.password == "env_pass"

    def test_credentials_from_env_missing_raises(self) -> None:
        """Test that missing environment variables raises CredentialError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(CredentialError, match="not set"):
                Credentials.from_env()


class TestBotConfig:
    """Tests for the BotConfig class."""

    def test_default_config(self) -> None:
        """Test creating config with default values."""
        config = BotConfig()
        assert config.ask_mode is False
        assert config.auto_approve_all is False
        assert config.dry_run is False
        assert config.category_limit == DEFAULT_CATEGORY_LIMIT
        assert config.edit_summary == DEFAULT_EDIT_SUMMARY
        assert config.rate_limit == DEFAULT_RATE_LIMIT
        assert config.max_edits_per_run == 0
        assert config.log_level == LogLevel.INFO

    def test_custom_config(self) -> None:
        """Test creating config with custom values."""
        config = BotConfig(
            ask_mode=True,
            category_limit=100,
            rate_limit=5.0,
            log_level=LogLevel.DEBUG,
        )
        assert config.ask_mode is True
        assert config.category_limit == 100
        assert config.rate_limit == 5.0
        assert config.log_level == LogLevel.DEBUG

    def test_invalid_category_limit_raises(self) -> None:
        """Test that negative category limit raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="must be non-negative"):
            BotConfig(category_limit=-1)

    def test_invalid_rate_limit_raises(self) -> None:
        """Test that non-positive rate limit raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="must be positive"):
            BotConfig(rate_limit=0)

    def test_edit_tracking(self) -> None:
        """Test edit counting functionality."""
        config = BotConfig(max_edits_per_run=5)
        assert config.edits_made == 0
        assert config.can_edit is True
        assert config.edits_remaining == 5

        config.record_edit()
        assert config.edits_made == 1
        assert config.can_edit is True
        assert config.edits_remaining == 4

        for _ in range(4):
            config.record_edit()
        assert config.edits_made == 5
        assert config.can_edit is False
        assert config.edits_remaining == 0

    def test_unlimited_edits(self) -> None:
        """Test that max_edits_per_run=0 means unlimited."""
        config = BotConfig(max_edits_per_run=0)
        assert config.can_edit is True
        assert config.edits_remaining is None

        config.record_edit()
        assert config.can_edit is True
        assert config.edits_remaining is None

    def test_for_interactive(self) -> None:
        """Test the for_interactive factory method."""
        config = BotConfig.for_interactive()
        assert config.ask_mode is True
        assert config.category_limit == 10
        assert config.log_level == LogLevel.DEBUG

    def test_for_production(self) -> None:
        """Test the for_production factory method."""
        config = BotConfig.for_production()
        assert config.ask_mode is False
        assert config.category_limit == DEFAULT_CATEGORY_LIMIT
        assert config.log_level == LogLevel.INFO

    def test_to_dict(self) -> None:
        """Test converting config to dictionary."""
        config = BotConfig(ask_mode=True, category_limit=50)
        d = config.to_dict()
        assert d["ask_mode"] is True
        assert d["category_limit"] == 50
        assert "has_credentials" in d

    def test_approval_without_ask_mode(self) -> None:
        """Test that approval is automatic when not in ask mode."""
        config = BotConfig(ask_mode=False)
        decision = config.request_approval("Test", "old", "new")
        assert decision == ApprovalDecision.APPROVE

    def test_approval_with_auto_approve_all(self) -> None:
        """Test that auto_approve_all skips all confirmations."""
        config = BotConfig(ask_mode=True, auto_approve_all=True)
        decision = config.request_approval("Test", "old", "new")
        assert decision == ApprovalDecision.APPROVE

    def test_custom_approval_handler(self) -> None:
        """Test using a custom approval handler."""
        config = BotConfig(ask_mode=True)

        def handler(page: str, old: str, new: str) -> ApprovalDecision:
            return ApprovalDecision.REJECT

        config.set_approval_handler(handler)
        decision = config.request_approval("Test", "old", "new")
        assert decision == ApprovalDecision.REJECT


class TestApprovalDecision:
    """Tests for the ApprovalDecision enum."""

    def test_decision_values(self) -> None:
        """Test that all decisions have unique values."""
        values = [d.value for d in ApprovalDecision]
        assert len(values) == len(set(values))


class TestLogLevel:
    """Tests for the LogLevel enum."""

    def test_log_level_values(self) -> None:
        """Test that log levels match Python logging values."""
        assert LogLevel.DEBUG.value == 10
        assert LogLevel.INFO.value == 20
        assert LogLevel.WARNING.value == 30
        assert LogLevel.ERROR.value == 40
        assert LogLevel.CRITICAL.value == 50


# =============================================================================
# Exception Tests
# =============================================================================

class TestExceptions:
    """Tests for the exception hierarchy."""

    def test_bot_error_basic(self) -> None:
        """Test creating a basic BotError."""
        e = BotError("Test error")
        assert str(e) == "Test error"
        assert e.message == "Test error"
        assert e.cause is None

    def test_bot_error_with_cause(self) -> None:
        """Test BotError with underlying cause."""
        original = ValueError("original")
        e = BotError("Test error", cause=original)
        assert e.cause == original
        assert e.__cause__ == original

    def test_credential_error(self) -> None:
        """Test CredentialError with credential type."""
        e = CredentialError("Invalid", credential_type="username")
        assert e.credential_type == "username"

    def test_api_error_with_details(self) -> None:
        """Test APIError with operation details."""
        e = APIError(
            "Failed",
            operation="query",
            api_code="missingtitle",
            api_info="Title not found"
        )
        assert "operation=query" in str(e)
        assert "code=missingtitle" in str(e)
        assert "info=Title not found" in str(e)

    def test_rate_limit_error(self) -> None:
        """Test RateLimitError with retry_after."""
        e = RateLimitError(retry_after=30.0, limit_type="requests")
        assert e.retry_after == 30.0
        assert e.limit_type == "requests"

    def test_category_processing_error(self) -> None:
        """Test CategoryProcessingError includes category in message."""
        e = CategoryProcessingError("No link found", category="TestCat")
        assert e.category == "TestCat"
        assert "[TestCat]" in str(e)

    def test_page_processing_error(self) -> None:
        """Test PageProcessingError includes page title."""
        e = PageProcessingError(
            "Edit failed",
            page_title="TestPage",
            category="TestCategory"
        )
        assert e.page_title == "TestPage"
        assert e.category == "TestCategory"
        assert "TestPage" in str(e)
        assert "TestCategory" in str(e)

    def test_edit_error(self) -> None:
        """Test EditError with edit summary."""
        e = EditError(
            "Protected page",
            page_title="Main Page",
            edit_summary="Bot edit"
        )
        assert e.page_title == "Main Page"
        assert e.edit_summary == "Bot edit"

    def test_validation_error(self) -> None:
        """Test ValidationError with field info."""
        e = ValidationError(
            "Invalid value",
            field="category_name",
            value=""
        )
        assert e.field == "category_name"
        assert e.value == ""

    def test_exception_inheritance(self) -> None:
        """Test that all exceptions inherit from BotError."""
        exceptions = [
            CredentialError("test"),
            APIError("test"),
            CategoryProcessingError("test"),
            ValidationError("test"),
        ]
        for e in exceptions:
            assert isinstance(e, BotError)


# =============================================================================
# Rate Limiter Tests
# =============================================================================

class TestSimpleRateLimiter:
    """Tests for SimpleRateLimiter."""

    def test_basic_rate_limiting(self) -> None:
        """Test that rate limiting enforces minimum interval."""
        limiter = SimpleRateLimiter(calls_per_second=100.0)  # 10ms interval

        start = time.time()
        for _ in range(3):
            limiter.acquire()
        elapsed = time.time() - start

        # Should take at least 20ms for 3 calls at 100/sec
        assert elapsed >= 0.015  # Allow some tolerance

    def test_rate_limit_context_manager(self) -> None:
        """Test using rate limiter as context manager."""
        limiter = SimpleRateLimiter(calls_per_second=100.0)

        with limiter:
            pass  # Simulated API call

        assert limiter.last_call_time > 0

    def test_rate_limit_stats(self) -> None:
        """Test that statistics are tracked."""
        limiter = SimpleRateLimiter(calls_per_second=1000.0)

        limiter.acquire()
        limiter.acquire()

        stats = limiter.get_stats()
        assert isinstance(stats, dict)
        assert "total_waits" in stats
        assert "total_wait_time" in stats

    def test_invalid_rate_raises(self) -> None:
        """Test that invalid rate raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            SimpleRateLimiter(calls_per_second=0)

        with pytest.raises(ValueError, match="must be positive"):
            SimpleRateLimiter(calls_per_second=-1)

    def test_reset_clears_state(self) -> None:
        """Test that reset clears the last call time."""
        limiter = SimpleRateLimiter(calls_per_second=100.0)
        limiter.acquire()
        assert limiter.last_call_time > 0

        limiter.reset()
        # After reset, next call should be immediate
        start = time.time()
        limiter.acquire()
        elapsed = time.time() - start
        assert elapsed < 0.005  # Should be nearly instant


class TestTokenBucketRateLimiter:
    """Tests for TokenBucketRateLimiter."""

    def test_burst_capacity(self) -> None:
        """Test that burst requests are allowed."""
        limiter = TokenBucketRateLimiter(rate=10.0, burst=5)

        # First 5 calls should be instant (burst capacity)
        start = time.time()
        for _ in range(5):
            limiter.acquire()
        elapsed = time.time() - start

        assert elapsed < 0.05  # All should be instant

    def test_rate_limiting_after_burst(self) -> None:
        """Test that rate limiting kicks in after burst is exhausted."""
        limiter = TokenBucketRateLimiter(rate=100.0, burst=2)

        # Exhaust burst
        limiter.acquire()
        limiter.acquire()

        # Next calls should be rate limited
        start = time.time()
        limiter.acquire()
        limiter.acquire()
        elapsed = time.time() - start

        # At 100/sec, 2 calls should take at least 10ms
        assert elapsed >= 0.01

    def test_invalid_burst_raises(self) -> None:
        """Test that invalid burst raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            TokenBucketRateLimiter(rate=10.0, burst=0)

    def test_acquire_more_than_burst_raises(self) -> None:
        """Test that acquiring more than burst capacity raises."""
        limiter = TokenBucketRateLimiter(rate=10.0, burst=5)
        with pytest.raises(ValueError, match="burst capacity"):
            limiter.acquire(10)

    def test_release_refunds_tokens(self) -> None:
        """Test that release returns tokens to bucket."""
        limiter = TokenBucketRateLimiter(rate=10.0, burst=5)

        limiter.acquire()
        tokens_after_acquire = limiter.tokens

        limiter.release()
        tokens_after_release = limiter.tokens

        assert tokens_after_release > tokens_after_acquire


class TestAdaptiveRateLimiter:
    """Tests for AdaptiveRateLimiter."""

    def test_initial_rate(self) -> None:
        """Test that initial rate is set correctly."""
        limiter = AdaptiveRateLimiter(initial_rate=5.0)
        assert limiter.current_rate == 5.0

    def test_success_increases_rate(self) -> None:
        """Test that consecutive successes increase rate."""
        limiter = AdaptiveRateLimiter(
            initial_rate=5.0,
            min_rate=1.0,
            max_rate=20.0
        )

        # Simulate 10 consecutive successes
        for _ in range(10):
            limiter.on_success()

        assert limiter.current_rate > 5.0

    def test_rate_limit_decreases_rate(self) -> None:
        """Test that rate limiting decreases rate."""
        limiter = AdaptiveRateLimiter(
            initial_rate=10.0,
            min_rate=1.0,
            max_rate=20.0
        )

        limiter.on_rate_limited()

        assert limiter.current_rate < 10.0

    def test_rate_never_below_minimum(self) -> None:
        """Test that rate never goes below minimum."""
        limiter = AdaptiveRateLimiter(
            initial_rate=5.0,
            min_rate=2.0,
            max_rate=20.0
        )

        # Multiple rate limit events
        for _ in range(10):
            limiter.on_rate_limited()

        assert limiter.current_rate >= 2.0

    def test_rate_never_above_maximum(self) -> None:
        """Test that rate never exceeds maximum."""
        limiter = AdaptiveRateLimiter(
            initial_rate=5.0,
            min_rate=1.0,
            max_rate=10.0
        )

        # Many successes
        for _ in range(100):
            limiter.on_success()

        assert limiter.current_rate <= 10.0


class TestCreateRateLimiter:
    """Tests for the create_rate_limiter factory function."""

    def test_create_simple(self) -> None:
        """Test creating a simple rate limiter."""
        limiter = create_rate_limiter("simple", calls_per_second=5.0)
        assert isinstance(limiter, SimpleRateLimiter)

    def test_create_token_bucket(self) -> None:
        """Test creating a token bucket rate limiter."""
        limiter = create_rate_limiter("token_bucket", rate=10.0, burst=5)
        assert isinstance(limiter, TokenBucketRateLimiter)

    def test_create_adaptive(self) -> None:
        """Test creating an adaptive rate limiter."""
        limiter = create_rate_limiter("adaptive", initial_rate=5.0)
        assert isinstance(limiter, AdaptiveRateLimiter)

    def test_invalid_strategy_raises(self) -> None:
        """Test that invalid strategy raises ValueError."""
        with pytest.raises(ValueError, match="Unknown strategy"):
            create_rate_limiter("invalid")


# =============================================================================
# Type Tests
# =============================================================================

class TestTypes:
    """Tests for type definitions and helpers."""

    def test_is_valid_page_with_valid_object(self) -> None:
        """Test is_valid_page with a compliant object."""
        class ValidPage:
            name = "Test"
            namespace = 0
            site = None

            def text(self) -> str:
                return "content"

            def save(self, text: str, *, summary: str) -> dict:
                return {}

            def redirects_to(self) -> None:
                return None

            def langlinks(self) -> list:
                return []

        page = ValidPage()
        assert is_valid_page(page) is True

    def test_is_valid_page_with_invalid_object(self) -> None:
        """Test is_valid_page with a non-compliant object."""
        class InvalidPage:
            pass

        page = InvalidPage()
        assert is_valid_page(page) is False

    def test_is_valid_site_with_valid_object(self) -> None:
        """Test is_valid_site with a compliant object."""
        class ValidSite:
            def get(self, action: str, **kwargs) -> dict:
                return {}

            def api(self, **kwargs) -> dict:
                return {}

            def login(self, username: str, password: str) -> None:
                pass

            @property
            def pages(self):
                return {}

        site = ValidSite()
        assert is_valid_site(site) is True


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
