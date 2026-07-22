"""
Rate Limiting Utilities for Wikipedia Bot Applications.

This module provides rate limiting functionality to prevent the bot from
overwhelming the Wikipedia API with too many requests. Wikipedia has strict
rate limits, and exceeding them can result in IP blocks or throttling.

The module provides both simple and token-bucket rate limiting strategies:

- SimpleRateLimiter: Basic rate limiting with fixed intervals between calls
- TokenBucketRateLimiter: Advanced rate limiting allowing burst requests

Example:
    Basic usage with SimpleRateLimiter::

        from utils.rate_limiter import SimpleRateLimiter

        limiter = SimpleRateLimiter(calls_per_second=10.0)

        with limiter:
            result = api.get_category_members(...)

    Using token bucket for burst handling::

        from utils.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(
            rate=10.0,  # 10 calls per second sustained
            burst=50,   # Allow up to 50 calls in a burst
        )

        for category in categories:
            with limiter:
                process(category)

Notes:
    - Rate limiting is thread-safe by default
    - Use context managers for automatic rate limiting
    - The default rate (10 calls/sec) is safe for most Wikipedia bots
    - Bot accounts may have higher rate limits than anonymous users

"""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock

from .exceptions import RateLimitError

# =============================================================================
# Constants
# =============================================================================

# Default rate: 10 calls per second (safe for most bots)
DEFAULT_CALLS_PER_SECOND: float = 10.0

# Minimum time between requests (in seconds)
MIN_REQUEST_INTERVAL: float = 0.1  # 100ms minimum

# Maximum wait time before raising an error (in seconds)
MAX_WAIT_TIME: float = 60.0


# =============================================================================
# Simple Rate Limiter
# =============================================================================


class SimpleRateLimiter:
    """
    A simple thread-safe rate limiter using fixed intervals.

    This rate limiter enforces a minimum time interval between API calls.
    It's suitable for most use cases where consistent, predictable rate
    limiting is needed.

    The limiter uses a simple approach: before each call, it checks if
    enough time has passed since the last call. If not, it waits.

    Attributes:
        calls_per_second: Maximum number of calls allowed per second.
        min_interval: Minimum time between calls (reciprocal of rate).
        last_call_time: Timestamp of the last call.

    Example:
        >>> limiter = SimpleRateLimiter(calls_per_second=5.0)
        >>> with limiter:
        ...     make_api_call()  # Will wait if called too soon

    Thread Safety:
        This class is thread-safe. Multiple threads can share the same
        limiter instance and calls will be properly serialized.

    """

    def __init__(
        self,
        calls_per_second: float = DEFAULT_CALLS_PER_SECOND,
        *,
        max_wait: float = MAX_WAIT_TIME,
    ) -> None:
        """
        Initialize a SimpleRateLimiter.

        Args:
            calls_per_second: Maximum calls per second. Must be positive.
                Defaults to 10.0 (10 calls per second).
            max_wait: Maximum time to wait for rate limit in seconds.
                If wait would exceed this, raises RateLimitError.
                Defaults to 60 seconds.

        Raises:
            ValueError: If calls_per_second is not positive.

        """
        if calls_per_second <= 0:
            raise ValueError(f"calls_per_second must be positive, got {calls_per_second}")

        self.calls_per_second = calls_per_second
        self.min_interval = max(1.0 / calls_per_second, MIN_REQUEST_INTERVAL)
        self.max_wait = max_wait
        self._last_call_time: float = 0.0
        self._lock = Lock()
        self._total_waits = 0
        self._total_wait_time = 0.0

    @property
    def last_call_time(self) -> float:
        """Get the timestamp of the last call."""
        with self._lock:
            return self._last_call_time

    def acquire(self) -> None:
        """
        Acquire permission to make a call, waiting if necessary.

        This method blocks until it's safe to make an API call according
        to the rate limit. It should be called before each API request.

        Raises:
            RateLimitError: If the required wait time exceeds max_wait.

        """
        with self._lock:
            current_time = time.time()
            time_since_last = current_time - self._last_call_time
            wait_time = self.min_interval - time_since_last

            if wait_time > 0:
                if wait_time > self.max_wait:
                    raise RateLimitError(
                        f"Required wait time ({wait_time:.2f}s) exceeds maximum ({self.max_wait:.2f}s)",
                        retry_after=wait_time,
                        limit_type="rate_limit",
                    )

                time.sleep(wait_time)
                self._total_waits += 1
                self._total_wait_time += wait_time

            self._last_call_time = time.time()

    def release(self) -> None:
        """
        Release the rate limiter (no-op for simple limiter).

        This method is provided for API compatibility with other limiter
        types. For SimpleRateLimiter, it does nothing.

        """

    def reset(self) -> None:
        """
        Reset the rate limiter state.

        This clears the last call time, allowing the next call to proceed
        immediately. Use with caution.

        """
        with self._lock:
            self._last_call_time = 0.0

    def get_stats(self) -> dict[str, float | int]:
        """
        Get statistics about rate limiting.

        Returns:
            Dictionary containing:
            - total_waits: Number of times the limiter had to wait
            - total_wait_time: Total time spent waiting (seconds)
            - avg_wait_time: Average wait time (seconds)

        """
        with self._lock:
            avg_wait = self._total_wait_time / self._total_waits if self._total_waits > 0 else 0.0
            return {
                "total_waits": self._total_waits,
                "total_wait_time": self._total_wait_time,
                "avg_wait_time": avg_wait,
            }

    @contextmanager
    def limit(self) -> Generator[None]:
        """
        Context manager for rate-limited operations.

        This is the recommended way to use the rate limiter. It ensures
        that the rate limit is respected before the operation starts.

        Yields:
            None

        Example:
            >>> with limiter.limit():
            ...     result = api.query(...)

        """
        self.acquire()
        try:
            yield
        finally:
            self.release()

    def __enter__(self) -> SimpleRateLimiter:
        """Enter context manager - acquire rate limit."""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager - release rate limit."""
        self.release()


# =============================================================================
# Token Bucket Rate Limiter
# =============================================================================


@dataclass
class TokenBucketRateLimiter:
    """
    A token bucket rate limiter allowing burst requests.

    This rate limiter uses the token bucket algorithm, which allows
    for burst requests up to the bucket capacity while maintaining
    an average rate over time.

    How it works:
    - Tokens are added to the bucket at a fixed rate
    - Each request consumes one token
    - If the bucket is empty, requests must wait
    - The bucket has a maximum capacity (burst size)

    This is useful when you need to make many requests quickly
    (e.g., fetching a large category) but still respect the
    overall rate limit.

    Attributes:
        rate: Tokens added per second (sustained rate).
        burst: Maximum tokens in bucket (burst capacity).
        tokens: Current number of tokens in bucket.

    Example:
        >>> limiter = TokenBucketRateLimiter(
        ...     rate=10.0,  # 10 calls/second sustained
        ...     burst=50,   # Up to 50 calls in a burst
        ... )
        >>> for _ in range(100):
        ...     with limiter:
        ...         make_api_call()  # First 50 instant, then rate-limited

    Thread Safety:
        This class is thread-safe when created with thread_safe=True.

    """

    rate: float = DEFAULT_CALLS_PER_SECOND
    burst: int = 50
    max_wait: float = MAX_WAIT_TIME
    thread_safe: bool = True

    _tokens: float = field(default=0.0, init=False, repr=False)
    _last_update: float = field(default=0.0, init=False, repr=False)
    _lock: Lock | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize the rate limiter after dataclass creation."""
        if self.rate <= 0:
            raise ValueError(f"rate must be positive, got {self.rate}")
        if self.burst <= 0:
            raise ValueError(f"burst must be positive, got {self.burst}")

        # Start with full bucket
        self._tokens = float(self.burst)
        self._last_update = time.time()

        if self.thread_safe:
            self._lock = Lock()

    def _get_lock(self) -> Lock:
        """Get the lock, creating a dummy if not thread-safe."""
        if self._lock is None:
            # Create a no-op context manager for single-threaded use
            @contextmanager
            def noop_lock():
                yield

            return noop_lock()  # type: ignore
        return self._lock

    @property
    def tokens(self) -> float:
        """Get the current number of tokens (after refill)."""
        with self._get_lock():
            self._refill()
            return self._tokens

    def _refill(self) -> None:
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self._last_update

        # Add tokens for elapsed time
        new_tokens = elapsed * self.rate
        self._tokens = min(float(self.burst), self._tokens + new_tokens)
        self._last_update = now

    def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire. Defaults to 1.

        Raises:
            RateLimitError: If wait time exceeds max_wait.
            ValueError: If requesting more tokens than burst capacity.

        """
        if tokens > self.burst:
            raise ValueError(f"Cannot acquire {tokens} tokens; burst capacity is {self.burst}")

        with self._get_lock():
            self._refill()

            if self._tokens >= tokens:
                self._tokens -= tokens
                return

            # Calculate wait time
            tokens_needed = tokens - self._tokens
            wait_time = tokens_needed / self.rate

            if wait_time > self.max_wait:
                raise RateLimitError(
                    f"Required wait time ({wait_time:.2f}s) exceeds maximum ({self.max_wait:.2f}s)",
                    retry_after=wait_time,
                    limit_type="rate_limit",
                )

            time.sleep(wait_time)
            self._refill()
            self._tokens -= tokens

    def release(self, tokens: int = 1) -> None:
        """
        Return tokens to the bucket.

        This can be used if a request fails and you want to "refund"
        the token. The bucket will not exceed its burst capacity.

        Args:
            tokens: Number of tokens to return. Defaults to 1.

        """
        with self._get_lock():
            self._tokens = min(float(self.burst), self._tokens + tokens)

    def reset(self) -> None:
        """Reset the bucket to full capacity."""
        with self._get_lock():
            self._tokens = float(self.burst)
            self._last_update = time.time()

    @contextmanager
    def limit(self, tokens: int = 1) -> Generator[None]:
        """
        Context manager for rate-limited operations.

        Args:
            tokens: Number of tokens to consume.

        Yields:
            None

        """
        self.acquire(tokens)
        try:
            yield
        except Exception:
            # Refund the token on failure
            self.release(tokens)
            raise

    def __enter__(self) -> TokenBucketRateLimiter:
        """Enter context manager."""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        if exc_type is not None:
            self.release()


# =============================================================================
# Adaptive Rate Limiter
# =============================================================================


class AdaptiveRateLimiter:
    """
    A rate limiter that adapts based on API responses.

    This rate limiter monitors API responses and adjusts the rate
    automatically when it detects rate limiting or throttling.

    Features:
    - Automatically reduces rate on 429 responses
    - Gradually increases rate when successful
    - Maintains minimum and maximum bounds

    Example:
        >>> limiter = AdaptiveRateLimiter(
        ...     initial_rate=10.0,
        ...     min_rate=1.0,
        ...     max_rate=20.0,
        ... )
        >>> with limiter:
        ...     response = api.query(...)
        ...     limiter.update_from_response(response)

    """

    def __init__(
        self,
        initial_rate: float = DEFAULT_CALLS_PER_SECOND,
        min_rate: float = 1.0,
        max_rate: float = 50.0,
        *,
        backoff_factor: float = 0.5,
        recovery_factor: float = 1.1,
    ) -> None:
        """
        Initialize an AdaptiveRateLimiter.

        Args:
            initial_rate: Starting rate in calls per second.
            min_rate: Minimum rate (won't go below this).
            max_rate: Maximum rate (won't exceed this).
            backoff_factor: Multiplier when reducing rate (< 1.0).
            recovery_factor: Multiplier when increasing rate (> 1.0).

        """
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.backoff_factor = backoff_factor
        self.recovery_factor = recovery_factor

        self._limiter = SimpleRateLimiter(calls_per_second=initial_rate)
        self._consecutive_successes = 0
        self._lock = Lock()

    def acquire(self) -> None:
        """Acquire permission to make a call."""
        self._limiter.acquire()

    def release(self) -> None:
        """Release the rate limiter."""
        self._limiter.release()

    def on_success(self) -> None:
        """
        Called when an API request succeeds.

        This gradually increases the rate after consecutive successes.
        """
        with self._lock:
            self._consecutive_successes += 1

            # Increase rate every 10 consecutive successes
            if self._consecutive_successes >= 10:
                new_rate = min(self.current_rate * self.recovery_factor, self.max_rate)
                if new_rate != self.current_rate:
                    self.current_rate = new_rate
                    self._limiter = SimpleRateLimiter(calls_per_second=new_rate)
                self._consecutive_successes = 0

    def on_rate_limited(self, retry_after: float | None = None) -> None:
        """
        Called when an API request is rate-limited.

        This reduces the rate to avoid future throttling.

        Args:
            retry_after: Suggested wait time from the API (if provided).

        """
        with self._lock:
            self._consecutive_successes = 0

            # Reduce rate
            new_rate = max(self.current_rate * self.backoff_factor, self.min_rate)
            self.current_rate = new_rate
            self._limiter = SimpleRateLimiter(calls_per_second=new_rate)

            # Wait for retry_after if specified
            if retry_after and retry_after > 0:
                time.sleep(min(retry_after, MAX_WAIT_TIME))

    def update_from_response(
        self,
        response: dict,
        *,
        retry_after_header: str | None = None,
    ) -> None:
        """
        Update rate based on API response.

        Args:
            response: The API response dictionary.
            retry_after_header: Value of Retry-After header (if present).

        """
        # Check for rate limit error codes
        error = response.get("error", {})
        code = error.get("code", "")

        if code in ("ratelimited", "rate_exceeded", "throttled"):
            retry_after = None
            if retry_after_header:
                try:
                    retry_after = float(retry_after_header)
                except ValueError:
                    pass
            self.on_rate_limited(retry_after)
        else:
            self.on_success()

    @contextmanager
    def limit(self) -> Generator[None]:
        """Context manager for rate-limited operations."""
        self.acquire()
        try:
            yield
            self.on_success()
        except RateLimitError:
            self.on_rate_limited()
            raise

    def __enter__(self) -> AdaptiveRateLimiter:
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is RateLimitError:
            self.on_rate_limited()
        elif exc_type is None:
            self.on_success()


# =============================================================================
# Factory Function
# =============================================================================


def create_rate_limiter(
    strategy: str = "simple",
    **kwargs,
) -> SimpleRateLimiter | TokenBucketRateLimiter | AdaptiveRateLimiter:
    """
    Create a rate limiter based on the specified strategy.

    Args:
        strategy: The rate limiting strategy to use.
            - "simple": Basic fixed-interval rate limiting
            - "token_bucket": Token bucket allowing bursts
            - "adaptive": Self-adjusting based on API responses
        **kwargs: Additional arguments passed to the limiter constructor.

    Returns:
        A rate limiter instance.

    Raises:
        ValueError: If strategy is not recognized.

    Example:
        >>> limiter = create_rate_limiter("simple", calls_per_second=5.0)
        >>> limiter = create_rate_limiter("token_bucket", rate=10.0, burst=50)

    """
    strategies = {
        "simple": SimpleRateLimiter,
        "token_bucket": TokenBucketRateLimiter,
        "adaptive": AdaptiveRateLimiter,
    }

    if strategy not in strategies:
        raise ValueError(f"Unknown strategy: {strategy}. Available: {', '.join(strategies.keys())}")

    return strategies[strategy](**kwargs)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Constants
    "DEFAULT_CALLS_PER_SECOND",
    "MIN_REQUEST_INTERVAL",
    "MAX_WAIT_TIME",
    # Classes
    "SimpleRateLimiter",
    "TokenBucketRateLimiter",
    "AdaptiveRateLimiter",
    # Factory
    "create_rate_limiter",
]
