# UnusedCategories Bot - Source Package

## Project Overview

This package implements a **MediaWiki bot** that automatically populates unused categories on Arabic Wikipedia. The bot bridges the gap between Arabic and English Wikipedia by leveraging interwiki links to identify articles that should belong to unused Arabic categories.

### What the Project Does

1. Fetches unused categories from Arabic Wikipedia's `Special:UnusedCategories`
2. Finds equivalent English Wikipedia categories via interwiki links
3. Retrieves members of those English categories
4. Locates the Arabic counterparts of those articles
5. Appends the Arabic category to articles that lack it

### Main Modules and Components

| Module                     | Purpose                                                                                         |
| -------------------------- | ----------------------------------------------------------------------------------------------- |
| `start.py`                 | CLI entry point; parses `-cat:` arguments and `ask` mode flag                                   |
| `unused_categories_bot.py` | Core bot logic: category filtering, page analysis, edit workflow, cross-wiki processing         |
| `wiki_api.py`              | MediaWiki API utilities: category member retrieval, interwiki link resolution                   |
| `utils/`                   | Subpackage with configuration, exceptions, rate limiting, text processing, and type definitions |

### Technologies, Frameworks, and Dependencies

-   **Python 3.13+** (per `pyproject.toml` target)
-   **mwclient** - MediaWiki API client for bot operations
-   **pywikibot** - Used for diff display (`showDiff`) in interactive mode
-   **python-dotenv** - Environment variable loading from `.env` files
-   **colorlog** - Colored console logging
-   **pytest** - Test framework

---

## Architecture & Code Quality Review

### Code Organization

The codebase follows a reasonable package structure:

```
src/
  __init__.py          # Exports main_entry
  start.py             # CLI argument parsing + entry point
  unused_categories_bot.py  # Core bot logic (~750 lines)
  wiki_api.py          # API interaction layer (~370 lines)
  utils/
    __init__.py        # Re-exports all utility symbols
    config.py          # BotConfig dataclass + Credentials
    exceptions.py      # Custom exception hierarchy
    rate_limiter.py    # Three rate limiter implementations
    text_utils.py      # Regex-based category text matching
    types.py           # TypedDict, Protocol, and type aliases
```

**Strengths of organization:**

-   Clear separation between API layer (`wiki_api.py`) and business logic (`unused_categories_bot.py`)
-   Utility subpackage isolates cross-cutting concerns
-   Type definitions are centralized in `types.py`

**Weaknesses of organization:**

-   `unused_categories_bot.py` is a monolithic 750-line module mixing connection management, category analysis, page analysis, edit logic, and orchestration
-   Global mutable state (`_config`, `_ask_mode`, `_auto_approve_all`) creates implicit coupling

### Design Patterns Used

| Pattern                          | Usage                                                                               | Assessment                                   |
| -------------------------------- | ----------------------------------------------------------------------------------- | -------------------------------------------- |
| **Dataclass**                    | `BotConfig`, `Credentials`                                                          | Well-used with validation in `__post_init__` |
| **Factory Method**               | `BotConfig.from_env()`, `BotConfig.for_interactive()`, `BotConfig.for_production()` | Clean, idiomatic                             |
| **Protocol (Structural Typing)** | `MediaWikiPage`, `MediaWikiSite`, `PageAccessor`                                    | Excellent for testability and mock support   |
| **Custom Exception Hierarchy**   | `BotError` -> `ConfigurationError`, `APIError`, `ProcessingError`                   | Well-designed with context attributes        |
| **Context Manager**              | Rate limiters (`with limiter:`)                                                     | Correct implementation                       |
| **Strategy Pattern**             | `create_rate_limiter()` factory with "simple", "token_bucket", "adaptive"           | Good extensibility                           |

### Maintainability

-   **Moderate.** The core bot module is too large and should be split. Functions are well-documented with docstrings, but the interplay between global state and `BotConfig` creates confusion.
-   Commented-out imports (`# , TYPE_CHECKING`, `# ApprovalDecision,`) suggest incomplete refactoring.

### Readability

-   **Good.** Consistent use of section headers (`# ====`), comprehensive docstrings with `Args/Returns/Example` sections, and meaningful variable names.
-   The color markup in log messages (e.g., `<<green>>`, `<<yellow>>`) is a custom convention that could confuse new contributors without documentation.

### Scalability Considerations

-   Rate limiting is properly implemented with three strategies (simple, token bucket, adaptive).
-   The `sub_cats_query` function uses `gcmlimit=max` which could be memory-intensive for very large categories.
-   No pagination support for `get_unused_categories` -- it fetches a single batch up to `limit`.

---

## Strengths

1. **Robust exception hierarchy** - Custom exceptions with contextual attributes (`category`, `page_title`, `api_code`) enable precise error handling and logging.

2. **Protocol-based type system** - `MediaWikiPage` and `MediaWikiSite` protocols allow mock-based testing without monkey-patching.

3. **Flexible rate limiting** - Three strategies (simple, token bucket, adaptive) with a factory function. Thread-safe implementations with proper locking.

4. **Interactive approval workflow** - The `ask` mode with diff display, bulk approval (`a`), and clean interrupt handling is well-implemented.

5. **Bilingual category handling** - Properly handles both Arabic (`تصنيف`) and English (`Category`) namespace prefixes in regex patterns.

6. **Configuration encapsulation** - `BotConfig` dataclass with environment variable loading, validation, and preset factories replaces what was likely messy global state.

7. **Comprehensive docstrings** - Nearly every public function has a complete docstring with Args, Returns, Examples, and Notes sections.

---

## Weaknesses

### 1. Monolithic Core Module

`unused_categories_bot.py` at ~750 lines handles too many responsibilities:

-   Credential management
-   Wikipedia site connection
-   Category filtering logic
-   Page redirect detection
-   Edit workflow (confirmation, dry run, saving)
-   Orchestration of the full pipeline

**Recommendation:** Split into `connection.py`, `category_filters.py`, `page_editor.py`, and `pipeline.py`.

### 2. Global Mutable State

```python
# unused_categories_bot.py
_config: Optional[BotConfig] = None
_ask_mode: bool = False
_auto_approve_all: bool = False
```

This creates hidden dependencies and makes testing fragile. The deprecated `set_ask_mode()` and `is_ask_mode()` functions mutate both global state AND the config object, leading to potential inconsistencies.

### 3. Inconsistent Error Handling

Some functions catch broad `Exception` while others only catch specific errors:

```python
# In categories_processor():
except Exception as e:
    logger.exception(f"Unexpected error processing category {category}: {e}")

# But in load_sites(), only specific errors are caught:
except mwclient.errors.LoginError as e:
    ...
except mwclient.errors.APIError as e:
    ...
```

### 4. Dead/Commented-Out Code

Multiple commented-out imports suggest incomplete refactoring:

```python
from typing import Final, Optional  # , TYPE_CHECKING
from .utils.config import (  # ApprovalDecision,
from .utils.exceptions import (  # CategoryProcessingError,; PageProcessingError,; EditError,; APIError,
```

### 5. Missing Type Annotations on Some Functions

`load_sites` and `categories_processor` lack parameter type annotations:

```python
def load_sites(username, password, rate_limiter):  # No types
def categories_processor(unused_categories, rate_limiter, ar_site, en_site) -> int:  # No param types
```

---

## Critical Issues

### 1. Credential Exposure Risk

The `.env` file contains live bot credentials:

```
WIKIPEDIA_BOT_USERNAME=Mr.Ibrahembot
WIKIPEDIA_BOT_PASSWORD=Mr.Ibrahembot@uh7qkaceq2jfb7qs03qhnl5p2r03k0r5
```

While `.env` is in `.gitignore`, the file exists on disk. If the `.gitignore` entry is ever removed or the repo is shared as a zip/tarball, credentials will leak. **Consider using a secret manager or encrypted credentials file.**

### 2. `is_credentials_loaded` Silently Swallows Errors

```python
def is_credentials_loaded() -> bool:
    try:
        username, password = load_credentials()
        return True
    except CredentialError as e:
        logger.error(str(e))
    return False
```

This loads credentials but discards them. The caller (`main_entry`) checks this boolean, then `start_work` loads credentials again. This is wasteful and creates a TOCTOU window.

### 3. No Retry Logic for API Failures

All API calls fail silently on error (return empty results). There is no retry mechanism for transient failures (network timeouts, temporary API errors). The `AdaptiveRateLimiter` exists but is never used in the actual bot code -- only `SimpleRateLimiter` is instantiated.

### 4. Race Condition in Rate Limiter

`SimpleRateLimiter.acquire()` calls `time.sleep()` while holding the lock:

```python
def acquire(self) -> None:
    with self._lock:
        ...
        if wait_time > 0:
            time.sleep(wait_time)  # Lock held during sleep!
```

This blocks all other threads from even checking the rate limit while one thread sleeps. For a single-threaded bot this is fine, but the class claims thread safety.

### 5. Unbounded Category Member Fetching

```python
def sub_cats_query(...):
    params = {
        "gcmlimit": API_MAX_LIMIT,  # "max" - could return thousands
        ...
    }
```

For categories with tens of thousands of members, this loads everything into memory at once with no pagination.

---

## Areas That Need Attention

### Missing Files

-   **No `__main__.py`** - Cannot run with `python -m src`
-   **No `py.typed` marker** - Type annotations won't be recognized by type checkers in consuming code
-   **No `CHANGELOG.md`** - No version history tracking

### Missing Documentation

-   The color markup convention (`<<green>>`, `<<yellow>>`, `<<red>>`, `<<purple>>`, `<<lightblue>>`) used in log messages is undocumented
-   No architecture decision records explaining the choice of mwclient vs pywikibot (both are used)
-   `types.py` defines `T_co` and `T_contra` type variables that are never used anywhere

### Lack of Tests

-   **No tests for `unused_categories_bot.py`** - The core module with the most complex logic has zero direct unit tests
-   Tests exist for: ask mode, credentials, get_unused_categories, is_hidden_category, redirects, text_utils
-   No integration tests that exercise the full pipeline
-   No tests for `wiki_api.py` functions

### Outdated Dependencies

-   `requirements.txt` has no version pins for `pywikibot` and `colorlog`
-   `pyproject.toml` targets Python 3.13 but `requirements.txt` says "Python 3.6+" -- contradictory

### Configuration Issues

-   `run.py` has `if setup_logging:` which is always truthy (it's a function reference), suggesting a bug or unclear intent
-   `start.py` duplicates logic that exists in `unused_categories_bot.py` (credential checking, category parsing)

---

## Improvement Plan

### Quick Wins (1-2 days)

1. Remove all commented-out imports and dead code
2. Add type annotations to `load_sites()` and `categories_processor()`
3. Fix `run.py`'s `if setup_logging:` check (should probably be `if setup_logging is not None:` or removed)
4. Add `__main__.py` to enable `python -m src` execution
5. Pin all dependency versions in `requirements.txt`

### Medium-Term Improvements (1-2 weeks)

1. **Split `unused_categories_bot.py`** into focused modules:
    - `connection.py` - `load_credentials()`, `connect_to_wikipedia()`, `load_sites()`
    - `category_filters.py` - `is_hidden_category()`, `should_skip_ar_category()`, `should_skip_en_category()`
    - `page_editor.py` - `add_category_to_page()`, `confirm_edit()`, `is_redirect_page()`
    - `pipeline.py` - `process_category()`, `categories_processor()`, `start_work()`
2. **Eliminate global state** - Pass `BotConfig` explicitly through all function calls
3. **Add retry logic** with exponential backoff for transient API failures
4. **Implement pagination** for `get_unused_categories()` and `sub_cats_query()`
5. **Use `AdaptiveRateLimiter`** instead of `SimpleRateLimiter` in production code

### Long-Term Refactoring (1+ months)

1. **Add comprehensive test coverage** for the core bot logic, including:
    - Mock-based tests using the existing `MediaWikiPage`/`MediaWikiSite` protocols
    - Integration test with recorded API responses
2. **Implement proper logging** instead of custom color markup in log messages (use structured logging)
3. **Add CI/CD pipeline** with linting (ruff), type checking (mypy), and test execution
4. **Create a proper CLI** using `argparse` or `click` instead of manual `sys.argv` parsing
5. **Add observability** - structured logging, metrics for edit counts, error rates, and processing times

---

## Comprehensive Review

| Metric                    | Score           | Notes                                                                                                                                                      |
| ------------------------- | --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Overall Rating**        | **6.5/10**      | Solid foundations, but needs structural cleanup                                                                                                            |
| **Production Readiness**  | Partially Ready | Works for manual/semi-automated runs; not ready for unattended production use without retry logic and better error recovery                                |
| **Technical Debt**        | Moderate        | Global state, monolithic module, commented-out code, unused type variables                                                                                 |
| **Risk Assessment**       | Medium          | Credential handling needs hardening; no retry logic means silent failures on transient errors; unbounded API responses could cause OOM on large categories |
| **Maintainability Score** | 6/10            | Good documentation and type hints, but the monolithic core module and global state make changes risky                                                      |
| **Test Coverage**         | Low-Medium      | Utils are well-tested; core bot logic has no direct tests                                                                                                  |
| **Code Quality**          | 7/10            | Clean style, good docstrings, proper use of dataclasses and protocols; undermined by global state and dead code                                            |
