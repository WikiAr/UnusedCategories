# UnusedCategories Bot - Utils Subpackage

## Project Overview

The `utils` subpackage provides cross-cutting infrastructure for the UnusedCategories bot. It encapsulates configuration management, error handling, rate limiting, text processing, and type definitions -- everything the core bot logic needs that isn't specific to Wikipedia category processing.

### Main Modules and Components

| Module | Lines | Purpose |
|--------|-------|---------|
| `config.py` | ~620 | `BotConfig` dataclass, `Credentials` dataclass, approval workflow, environment variable loading |
| `exceptions.py` | ~550 | Custom exception hierarchy rooted at `BotError` |
| `rate_limiter.py` | ~636 | Three rate limiter implementations: `SimpleRateLimiter`, `TokenBucketRateLimiter`, `AdaptiveRateLimiter` |
| `text_utils.py` | ~340 | Regex-based category detection in wikitext, stub/maintenance category filtering |
| `types.py` | ~645 | `TypedDict` classes for API responses, `Protocol` classes for MediaWiki interfaces, type aliases |

### Technologies, Frameworks, and Dependencies

- **pywikibot** - Used only in `config.py` for `showDiff()` in the interactive approval prompt
- **mwclient** - Referenced via Protocol definitions (not directly imported except in type hints)
- **threading.Lock** - Thread-safe rate limiting
- **dataclasses** - Configuration and rate limiter state
- **typing** - Extensive use of Protocol, TypedDict, Final, TypeVar, runtime_checkable
- **re** - Category pattern matching in wikitext

---

## Architecture & Code Quality Review

### Code Organization

Each module has a single, well-defined responsibility:

- **`config.py`**: Configuration + credentials + approval workflow (3 concerns, but tightly related)
- **`exceptions.py`**: Pure exception definitions, no logic
- **`rate_limiter.py`**: Pure rate limiting, no bot-specific knowledge
- **`text_utils.py`**: Pure text processing, no API calls
- **`types.py`**: Pure type definitions, no runtime logic (except validation helpers)

The `__init__.py` re-exports everything, providing a flat import surface:
```python
from utils import BotConfig, category_in_text, SimpleRateLimiter
```

### Design Patterns Used

| Pattern | Where | Quality |
|---------|-------|---------|
| **Dataclass** | `BotConfig`, `Credentials`, `TokenBucketRateLimiter` | Clean with `__post_init__` validation |
| **Factory Method** | `Credentials.from_env()`, `BotConfig.from_env()`, `BotConfig.for_interactive()`, `BotConfig.for_production()` | Excellent; provides named constructors |
| **Protocol (Structural Typing)** | `MediaWikiPage`, `MediaWikiSite`, `PageAccessor` | `@runtime_checkable` enables `isinstance()` checks |
| **Strategy Pattern** | `create_rate_limiter()` with string-based strategy selection | Good for extensibility |
| **Context Manager** | All rate limiters implement `__enter__`/`__exit__` and `limit()` | Clean resource management |
| **Template Method** | `AdaptiveRateLimiter` wraps `SimpleRateLimiter` and adjusts its rate | Well-structured |
| **Exception Hierarchy** | `BotError` -> `ConfigurationError` -> `CredentialError`; `BotError` -> `APIError` -> `RateLimitError`, `ConnectionError` | Comprehensive and well-documented |

### Maintainability

- **High.** Each module is self-contained with minimal cross-dependencies within the subpackage.
- `text_utils.py` has zero internal dependencies (only `re` and `functools`).
- `exceptions.py` has zero internal dependencies.
- `types.py` has zero internal dependencies.
- Only `config.py` imports from `exceptions.py`, and `rate_limiter.py` imports from `exceptions.py`.

### Readability

- **Excellent.** Every module has a comprehensive module-level docstring with usage examples.
- Every public class, method, and function has docstrings with Args/Returns/Example/Note sections.
- Consistent section headers (`# ====`) separate logical groups.
- Type annotations are thorough.

### Scalability Considerations

- `TokenBucketRateLimiter` and `AdaptiveRateLimiter` are well-designed for high-throughput scenarios.
- `text_utils.py` functions compile regex patterns on every call for `category_in_text()` -- could be cached for repeated lookups.
- `_build_category_pattern` returns a string (not compiled pattern), so callers compile it repeatedly.

---

## Strengths

### 1. Exception Design

The exception hierarchy is textbook-quality:

```python
BotError (base)
  +-- ConfigurationError
  |     +-- CredentialError
  +-- APIError
  |     +-- RateLimitError
  |     +-- ConnectionError
  +-- ProcessingError
  |     +-- CategoryProcessingError
  |     +-- PageProcessingError
  |     +-- EditError
  +-- ValidationError
```

Each exception carries contextual attributes (`category`, `page_title`, `api_code`, `retry_after`) and custom `__str__` methods for informative error messages.

### 2. Rate Limiter Implementations

Three distinct strategies serve different use cases:
- **`SimpleRateLimiter`**: Fixed-interval, predictable, good for steady workloads
- **`TokenBucketRateLimiter`**: Allows bursts while maintaining average rate; refunds tokens on failure
- **`AdaptiveRateLimiter`**: Self-tuning based on API response codes; backs off on 429s, recovers gradually

All are thread-safe, implement context managers, and expose statistics.

### 3. Protocol-Based Interfaces

```python
@runtime_checkable
class MediaWikiPage(Protocol):
    name: str
    namespace: int
    site: MediaWikiSite
    def text(self) -> str: ...
    def save(self, text: str, *, summary: str, ...) -> dict: ...
    def redirects_to(self) -> Optional[str]: ...
    def langlinks(self) -> list[tuple[str, str]]: ...
```

This enables:
- Static type checking with mypy
- Runtime `isinstance()` checks
- Clean mock objects for testing
- Decoupling from the mwclient library

### 4. Configuration Presets

```python
BotConfig.for_interactive()  # ask_mode=True, limit=10, DEBUG logging
BotConfig.for_production()   # ask_mode=False, limit=1000, INFO logging
```

This eliminates configuration errors for common use cases.

### 5. Text Utilities Robustness

`category_in_text()` handles:
- Both Arabic (`تصنيف`) and English (`Category`) prefixes
- Variable whitespace around colons and brackets
- Sort keys (`[[Category:Science|sort key]]`)
- Case-insensitive matching

---

## Weaknesses

### 1. `config.py` Has Too Many Responsibilities

The module handles:
- Credential management (`Credentials` dataclass)
- Bot configuration (`BotConfig` dataclass)
- Edit approval workflow (`ApprovalDecision`, `confirm_edit` logic)
- Interactive prompt UI (`_interactive_prompt` with `input()` calls)

The approval workflow and interactive prompt should be in a separate module (e.g., `approval.py`).

### 2. `BotConfig` Mixes Configuration with State

```python
@dataclass
class BotConfig:
    ask_mode: bool = False          # Configuration
    _edits_made: int = field(...)   # Mutable runtime state
    _approval_handler: ...          # Callback
```

Configuration should be immutable after creation. Mutable state (`_edits_made`, `auto_approve_all`) should live in a separate runtime context object.

### 3. Redundant Validation in `types.py`

The `is_valid_page()` and `is_valid_site()` functions duplicate what `@runtime_checkable` already provides:

```python
@runtime_checkable
class MediaWikiPage(Protocol):
    ...

def is_valid_page(obj: Any) -> bool:
    if not isinstance(obj, MediaWikiPage):  # Already checks Protocol
        return False
    required_attrs = ("name", "namespace", "site")  # Redundant
    ...
```

The `isinstance()` check with `@runtime_checkable` already verifies methods exist. The manual attribute checks add nothing.

### 4. `_build_category_pattern` Returns Uncompiled Pattern

```python
def _build_category_pattern(category_name: str, prefix_pattern: str) -> str:
    return r"\[\[\s*" + prefix_pattern + r"\s*:\s*" + re.escape(category_name) + r"\s*(?:\|[^\]]*?)?\]\]"

# Caller must compile every time:
def category_in_text(text: str, category_name: str) -> bool:
    pattern = _build_category_pattern(...)  # Builds string
    return bool(re.search(pattern, text, re.IGNORECASE))  # Compiles + searches
```

For repeated lookups on the same category, this wastes CPU re-compiling the same pattern.

### 5. `ConnectionError` Name Shadows Built-in

```python
class ConnectionError(APIError):  # Shadows built-in ConnectionError!
```

This shadows Python's built-in `ConnectionError` within any module that imports it. Should be renamed to `BotConnectionError` or `MediaWikiConnectionError`.

### 6. Unused Type Variables

`T_co` and `T_contra` are defined but never used:
```python
T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)      # Never used
T_contra = TypeVar("T_contra", contravariant=True)  # Never used
```

---

## Critical Issues

### 1. `pywikibot` Dependency for a Single Function

`config.py` imports `pywikibot` solely for `pywikibot.showDiff()` in the interactive prompt. This is a heavy dependency for a single utility function. If pywikibot is unavailable or misconfigured, the entire config module fails to import.

**Impact:** The bot cannot start without pywikibot installed, even in non-interactive mode.

### 2. Interactive Prompt Blocks the Thread

```python
def _interactive_prompt(self, ...):
    response = input("Confirm edit? [Y/n/a]: ").strip().lower()
```

This blocks indefinitely. In an async or GUI context, this would freeze the application. There's also no timeout mechanism.

### 3. `TokenBucketRateLimiter._get_lock()` Returns Wrong Type

```python
def _get_lock(self) -> Lock:
    if self._lock is None:
        @contextmanager
        def noop_lock():
            yield
        return noop_lock()  # Returns a Generator, not a Lock!
    return self._lock
```

The type annotation says `Lock` but it returns a context manager generator when `thread_safe=False`. This works at runtime because both are used with `with`, but it's a type lie.

### 4. `AdaptiveRateLimiter` Recreates `SimpleRateLimiter` on Every Backoff

```python
def on_rate_limited(self, retry_after=None):
    new_rate = max(self.current_rate * self.backoff_factor, self.min_rate)
    self.current_rate = new_rate
    self._limiter = SimpleRateLimiter(calls_per_second=new_rate)  # New object!
```

This creates a new `SimpleRateLimiter` on every rate limit event, losing the previous limiter's statistics and state.

### 5. Log Message Color Tags Are Not Escapable

`format_colored_text()` in the parent `logging_config.py` uses `<<color>>` syntax. If a log message legitimately contains `<<something>>`, it will be misinterpreted as a color tag. There's no escape mechanism.

---

## Areas That Need Attention

### Missing Files
- **No `py.typed`** marker for PEP 561 compliance
- **No `__all__` in `__init__.py`** -- actually it exists but contains a duplicate entry: `"has_ar_category_redirect_template"` appears twice (line 74)

### Missing Documentation
- The relationship between `BotConfig` and the deprecated global functions (`set_ask_mode`, `is_ask_mode`) in the parent module is not documented
- No documentation on when to use which rate limiter strategy
- `ApprovalDecision` enum values are not documented with their behavioral implications

### Lack of Tests
- **No tests for `rate_limiter.py`** - Three rate limiter implementations with zero test coverage
- **No tests for `config.py`** - BotConfig validation, from_env(), presets, approval workflow all untested
- **No tests for `types.py`** - Protocol validation helpers untested
- `text_utils.py` has good test coverage (multiple test files in `tests/text_utils/`)

### Configuration Issues
- `DEFAULT_CATEGORY_LIMIT = 1000` in `config.py` is also imported and re-exported as `DEFAULT_LIMIT` in `unused_categories_bot.py` -- single source of truth is unclear
- The `<<green>>` color tags in `config.py`'s `_interactive_prompt()` assume the parent logging module's colorizer is active, but `input()` prompts bypass the logging system

---

## Improvement Plan

### Quick Wins (1-2 days)
1. Remove unused type variables (`T_co`, `T_contra`)
2. Remove duplicate `has_ar_category_redirect_template` from `__all__` in `__init__.py`
3. Rename `ConnectionError` to `BotConnectionError` to avoid shadowing the built-in
4. Add type annotations to `_get_lock()` return type (use `Union[Lock, ContextManager]`)
5. Remove redundant `is_valid_page()`/`is_valid_site()` or document why they exist beyond `isinstance()`

### Medium-Term Improvements (1-2 weeks)
1. **Extract approval workflow** from `config.py` into `approval.py`
2. **Separate config from runtime state** - Create a `BotRuntime` or `BotSession` class for `_edits_made`, `auto_approve_all`
3. **Cache compiled regex patterns** in `text_utils.py` using `functools.lru_cache` or a pattern cache dict
4. **Remove pywikibot dependency** from `config.py` - Implement a simple diff display or use `difflib.unified_diff`
5. **Add comprehensive tests** for `rate_limiter.py`, `config.py`, and `types.py`

### Long-Term Refactoring (1+ months)
1. **Make `BotConfig` truly immutable** - Use `frozen=True` dataclass or `NamedTuple`
2. **Add async rate limiting** - Current implementations use `time.sleep()` which blocks the event loop
3. **Implement configuration validation schema** - Use pydantic or attrs for declarative validation
4. **Add structured logging** support - Replace custom `<<color>>` tags with proper structured log records
5. **Create a `conftest.py` with shared fixtures** - Mock `MediaWikiPage` and `MediaWikiSite` implementations for reuse across all test files

---

## Comprehensive Review

| Metric | Score | Notes |
|--------|-------|-------|
| **Overall Rating** | **7.5/10** | Well-designed infrastructure with clean separation of concerns |
| **Production Readiness** | Mostly Ready | Rate limiters and exceptions are production-quality; config needs state separation |
| **Technical Debt** | Low-Medium | Unused type variables, one name shadowing issue, redundant validation helpers |
| **Risk Assessment** | Low | These are utility modules with limited blast radius; the `pywikibot` dependency is the main risk |
| **Maintainability Score** | 8/10 | Self-contained modules, comprehensive docstrings, clean interfaces |
| **Test Coverage** | Low | Only `text_utils.py` has tests; `rate_limiter.py`, `config.py`, `types.py` are untested |
| **Code Quality** | 8/10 | Excellent documentation, proper use of advanced typing features, consistent style |
