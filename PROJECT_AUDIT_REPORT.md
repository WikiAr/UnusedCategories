# UnusedCategories Bot - Project Audit Report

> **Audit Date:** 2026-05-27
> **Auditor:** Automated Code Audit (Claude Code)
> **Scope:** Full codebase analysis of `src/`, `src/utils/`, project configuration, and test infrastructure
> **Repository Branch:** `up2` (base: `main`)

---

## Executive Summary

### Overall Purpose

UnusedCategories is a **MediaWiki bot** that automatically populates unused categories on Arabic Wikipedia. It bridges Arabic and English Wikipedia by:

1. Fetching unused categories from Arabic Wikipedia's `Special:UnusedCategories`
2. Resolving equivalent English categories via interwiki links
3. Retrieving English category members and their Arabic counterparts
4. Appending the Arabic category to articles that lack it

The bot operates across two wikis (ar.wikipedia.org, en.wikipedia.org) and handles bilingual category namespace conventions (`تصنيف` / `Category`).

### Main Technologies

| Technology | Version | Role |
|------------|---------|------|
| Python | 3.13+ (target) | Runtime |
| mwclient | >=0.10.0 | Primary MediaWiki API client |
| pywikibot | Unpinned | Diff display in interactive mode |
| python-dotenv | >=1.2.1 | Environment variable loading |
| colorlog | Unpinned | Colored console logging |
| pytest | >=9.0.2 | Test framework with coverage |

### General Architecture

```
run.py                          # Entry point + dotenv loading
  └─ src/
       ├─ start.py              # CLI argument parsing
       ├─ unused_categories_bot.py  # Core bot logic (750 lines)
       ├─ wiki_api.py           # MediaWiki API layer (370 lines)
       └─ utils/
            ├─ config.py        # BotConfig + Credentials + approval workflow
            ├─ exceptions.py    # Custom exception hierarchy
            ├─ rate_limiter.py  # 3 rate limiter implementations
            ├─ text_utils.py    # Regex-based wikitext processing
            └─ types.py         # TypedDict + Protocol definitions
```

The system follows a layered architecture: CLI (`run.py` / `start.py`) -> Pipeline (`unused_categories_bot.py`) -> API (`wiki_api.py`) -> Utilities (`utils/`). However, the pipeline layer is monolithic and mixes concerns.

---

## Project Health Assessment

| Dimension | Rating | Summary |
|-----------|--------|---------|
| **Overall Code Quality** | 6.5/10 | Clean style, good docstrings, proper typing -- undermined by global state and dead code |
| **Maintainability** | 6/10 | Good documentation, but monolithic core module and implicit coupling make changes risky |
| **Scalability** | 5/10 | Unbounded API responses, no pagination, single-batch processing, regex recompilation on every call |
| **Security Posture** | 5/10 | `.env` with live credentials on disk, no credential rotation, no input sanitization on category names |
| **Production Readiness** | Partial | Works for manual/semi-automated runs; not ready for unattended operation without retry logic, pagination, and error recovery |

---

## Cross-Project Analysis

### Shared Architectural Patterns

Both `src/` and `src/utils/` consistently apply:

- **Dataclass with `__post_init__` validation** -- `BotConfig`, `Credentials`, `TokenBucketRateLimiter`
- **Factory methods** -- `BotConfig.from_env()`, `BotConfig.for_interactive()`, `BotConfig.for_production()`, `Credentials.from_env()`
- **Protocol-based interfaces** -- `MediaWikiPage`, `MediaWikiSite`, `PageAccessor` with `@runtime_checkable`
- **Context manager pattern** -- All rate limiters implement `__enter__`/`__exit__` and `limit()`
- **Section-segmented source files** -- `# ====` headers separate logical groups in every file

### Repeated Weaknesses

| Weakness | Where It Appears |
|----------|-----------------|
| **Commented-out imports / dead code** | `unused_categories_bot.py`, `wiki_api.py`, `utils/__init__.py` |
| **Missing type annotations** | `load_sites()`, `categories_processor()` in bot module; `_get_lock()` return type in rate limiter |
| **Unused definitions** | `T_co`, `T_contra` in `types.py`; `AdaptiveRateLimiter` + `TokenBucketRateLimiter` defined but never instantiated in production code |
| **Duplicate definitions** | `has_ar_category_redirect_template` appears twice in `utils/__init__.__all__`; `DEFAULT_CATEGORY_LIMIT` defined in both `config.py` and re-exported as `DEFAULT_LIMIT` in bot module |
| **Inconsistent error handling** | Some paths catch broad `Exception`, others catch specific `mwclient.errors.*`, some silently return empty results |

### Common Technical Debt

1. **Incomplete migration from global state to `BotConfig`** -- Both patterns coexist, with deprecated functions (`set_ask_mode`, `is_ask_mode`) mutating both global variables and the config object.
2. **Heavy dependency for trivial use** -- `pywikibot` is imported in `config.py` solely for `pywikibot.showDiff()`, yet it's a required dependency for the entire application.
3. **No single source of truth for constants** -- `DEFAULT_CATEGORY_LIMIT` / `DEFAULT_LIMIT` / `DEFAULT_EDIT_SUMMARY` are defined in multiple places.
4. **Custom logging conventions undocumented** -- The `<<color>>` markup in log messages (`<<green>>`, `<<yellow>>`, `<<red>>`, `<<purple>>`, `<<lightblue>>`) is a project-specific convention with no documentation.

### Dependency Issues

| Issue | Severity |
|-------|----------|
| `pywikibot` unpinned in `requirements.txt` | Medium -- breaking changes possible |
| `colorlog` unpinned in `requirements.txt` | Low |
| `pyproject.toml` targets Python 3.13, but `README.md` says "Python 3.6+" | Low -- contradictory |
| `pywikibot` required at import time even for non-interactive mode | High -- unnecessary hard dependency |
| No `pyproject.toml` `[project]` section with dependency declarations | Medium -- `requirements.txt` and `pyproject.toml` serve overlapping roles |

### Integration Concerns

- **Two Wikipedia sites must be reachable** -- The bot connects to both `ar.wikipedia.org` and `en.wikipedia.org`. If either is down or rate-limiting, the entire pipeline fails with no retry.
- **Interwiki link dependency** -- If an Arabic category has no English interwiki link, it's silently skipped. There's no fallback strategy (e.g., Wikidata, search).
- **Edit conflict handling is absent** -- `page.save()` can raise `EditError` on conflicts, but the bot catches it generically and moves on without retry.

---

## Critical Findings

### HIGH RISK

#### 1. Credential Exposure

The `.env` file contains live bot credentials on disk:
```
WIKIPEDIA_BOT_USERNAME=Mr.Ibrahembot
WIKIPEDIA_BOT_PASSWORD=Mr.Ibrahembot@uh7qkaceq2jfb7qs03qhnl5p2r03k0r5
```

While `.env` is in `.gitignore` and not tracked by git, the file exists in the working directory. Risk scenarios:
- Repository shared as zip/tarball includes `.env`
- `.gitignore` entry accidentally removed
- Backup scripts capture the file
- `example.env` documents the pattern but contains no values (correct), but the real `.env` has no encryption

**Recommendation:** Use a secret manager, encrypted credentials file, or OS keyring.

#### 2. No Retry Logic for Transient API Failures

All API calls (`site.get()`, `site.api()`, `page.text()`, `page.save()`) fail silently on error, returning empty results or `False`. There is zero retry logic for:
- Network timeouts
- HTTP 429 (rate limited)
- HTTP 503 (service unavailable)
- Edit conflicts

The codebase defines `AdaptiveRateLimiter` (which handles 429 responses) but **never uses it** -- only `SimpleRateLimiter` is instantiated.

**Impact:** In production, any transient API error causes the bot to silently skip categories/articles with no recovery.

#### 3. Unbounded API Responses

```python
# wiki_api.py
params = {
    "gcmlimit": "max",  # No upper bound
    "lllimit": "max",
}
```

For categories with tens of thousands of members, this loads the entire response into memory. A single category like "Category:Living people" on English Wikipedia has 900,000+ members.

**Impact:** Potential `MemoryError` or extreme memory consumption on large categories.

#### 4. TOCTOU Credential Loading

```python
def is_credentials_loaded() -> bool:
    username, password = load_credentials()  # Loads + discards
    return True

def start_work(...):
    username, password = load_credentials()  # Loads again
```

Credentials are loaded twice -- once to check existence, once to use. Between these calls, environment variables could change, or the credential source could become unavailable.

### MEDIUM RISK

#### 5. `ConnectionError` Shadows Built-in

```python
# utils/exceptions.py
class ConnectionError(APIError):  # Shadows built-in ConnectionError
```

Any module importing `from utils.exceptions import ConnectionError` loses access to Python's built-in `ConnectionError`. This can cause subtle bugs in error handling.

#### 6. Rate Limiter Holds Lock During Sleep

```python
def acquire(self) -> None:
    with self._lock:
        if wait_time > 0:
            time.sleep(wait_time)  # Lock held!
```

For the current single-threaded usage this is harmless, but the class documents thread safety. In a multi-threaded scenario, this serializes all threads behind a single sleeper.

#### 7. `pywikibot` Import-Time Dependency

`config.py` imports `pywikibot` at module level for `showDiff()`. If pywikibot is not installed or misconfigured, **the entire bot fails to start**, even in non-interactive mode where `showDiff()` is never called.

### LOW RISK

#### 8. `TokenBucketRateLimiter._get_lock()` Type Mismatch

Returns a context manager generator when `thread_safe=False`, but annotated as `-> Lock`. Works at runtime due to duck typing, but breaks static analysis.

#### 9. Duplicate `__all__` Entry

`utils/__init__.py` exports `"has_ar_category_redirect_template"` twice in its `__all__` list.

#### 10. `run.py` Conditional Always True

```python
if setup_logging:  # Always truthy -- it's a function reference
    setup_logging(...)
```

This should be `if setup_logging is not None:` or removed entirely.

---

## Strengths

### 1. Exception Hierarchy Design

The custom exception tree is textbook quality:
```
BotError
  +-- ConfigurationError -> CredentialError
  +-- APIError -> RateLimitError, ConnectionError
  +-- ProcessingError -> CategoryProcessingError, PageProcessingError, EditError
  +-- ValidationError
```
Each exception carries contextual attributes (`category`, `page_title`, `api_code`, `retry_after`) and custom `__str__` methods. This enables precise error handling and logging.

### 2. Protocol-Based Type System

`MediaWikiPage`, `MediaWikiSite`, and `PageAccessor` protocols decouple the bot from the mwclient library. This enables:
- Clean mock-based testing without monkey-patching
- Static type checking with mypy
- Runtime `isinstance()` validation
- Library swaps without changing business logic

### 3. Rate Limiter Suite

Three implementations covering different use cases:
- `SimpleRateLimiter` -- predictable, steady workloads
- `TokenBucketRateLimiter` -- burst-tolerant with token refund on failure
- `AdaptiveRateLimiter` -- self-tuning based on API response codes

All are thread-safe, implement context managers, and expose statistics. A factory function (`create_rate_limiter()`) provides clean strategy selection.

### 4. Comprehensive Docstrings

Nearly every public function has complete docstrings with `Args`, `Returns`, `Raises`, `Example`, and `Note` sections. Module-level docstrings include usage examples. This is above average for a project of this size.

### 5. Bilingual Category Handling

`text_utils.py` correctly handles both Arabic (`تصنيف`) and English (`Category`) namespace prefixes with:
- Flexible whitespace matching
- Sort key support (`[[Category:Science|key]]`)
- Case-insensitive prefix matching
- Category redirect template detection (`{{تحويل تصنيف}}`)

### 6. Interactive Approval Workflow

The `ask` mode provides:
- Colorized diff display via `pywikibot.showDiff()`
- Per-edit approval (`y`/`n`) and bulk approval (`a`)
- Clean interrupt handling (`EOFError`, `KeyboardInterrupt`)
- Configurable approval handler injection

### 7. Clean Configuration Architecture

`BotConfig` with factory methods (`from_env()`, `for_interactive()`, `for_production()`) and preset configurations eliminates common misconfiguration scenarios. Validation in `__post_init__` catches invalid values early.

---

## Improvement Roadmap

### Immediate Fixes (1-3 days)

| # | Action | Impact |
|---|--------|--------|
| 1 | Remove all commented-out imports and dead code from `unused_categories_bot.py`, `wiki_api.py`, `utils/__init__.py` | Reduces confusion, improves readability |
| 2 | Add type annotations to `load_sites()` and `categories_processor()` | Enables static analysis |
| 3 | Rename `ConnectionError` to `BotConnectionError` in `utils/exceptions.py` | Eliminates built-in shadowing |
| 4 | Remove duplicate `has_ar_category_redirect_template` from `utils/__init__.__all__` | Fixes `__all__` correctness |
| 5 | Remove unused type variables `T_co`, `T_contra` from `types.py` | Dead code removal |
| 6 | Fix `run.py`'s `if setup_logging:` to `if setup_logging is not None:` | Bug fix |
| 7 | Pin `pywikibot` and `colorlog` versions in `requirements.txt` | Reproducible builds |
| 8 | Add `__main__.py` to `src/` | Enables `python -m src` execution |

### Short-Term Improvements (1-2 weeks)

| # | Action | Impact |
|---|--------|--------|
| 1 | **Split `unused_categories_bot.py`** into `connection.py`, `category_filters.py`, `page_editor.py`, `pipeline.py` | Reduces module from 750 lines to ~150-200 per file; enables focused testing |
| 2 | **Eliminate global state** -- pass `BotConfig` explicitly through all call chains; remove `_config`, `_ask_mode`, `_auto_approve_all` globals | Eliminates hidden coupling, makes testing deterministic |
| 3 | **Add retry logic with exponential backoff** for `page.text()`, `page.save()`, `site.get()`, `site.api()` | Prevents silent failures on transient errors |
| 4 | **Implement pagination** for `get_unused_categories()` and `sub_cats_query()` | Prevents OOM on large categories |
| 5 | **Lazy-import pywikibot** in `config.py` -- move `import pywikibot` inside `_interactive_prompt()` | Eliminates hard dependency for non-interactive mode |
| 6 | **Cache compiled regex patterns** in `text_utils.py` using `functools.lru_cache` | Reduces CPU on repeated category lookups |
| 7 | **Extract approval workflow** from `config.py` into `approval.py` | Separates UI concerns from configuration |
| 8 | **Add tests for `unused_categories_bot.py`** using Protocol-based mocks | Covers the highest-risk untested code |

### Long-Term Strategic Refactoring (1-3 months)

| # | Action | Impact |
|---|--------|--------|
| 1 | **Make `BotConfig` immutable** -- use `frozen=True` dataclass; create separate `BotSession` for mutable runtime state | Enforces configuration integrity |
| 2 | **Replace `pywikibot.showDiff()`** with `difflib.unified_diff` from stdlib | Eliminates heavy dependency entirely |
| 3 | **Create proper CLI** with `argparse` or `click` instead of manual `sys.argv` parsing | Adds help text, validation, shell completion |
| 4 | **Add CI/CD pipeline** -- ruff lint, mypy type check, pytest with coverage gates | Prevents regression |
| 5 | **Implement structured logging** -- replace custom `<<color>>` tags with `structlog` or `python-json-logger` | Machine-parseable logs, no custom parsing |
| 6 | **Add integration tests** with recorded API responses (VCR cassettes) | Tests real API contract without live calls |
| 7 | **Separate config from runtime state** -- `BotConfig` (frozen, from env/file) + `BotSession` (mutable, tracks edits, approval state) | Clean architecture |

### Security Hardening Priorities

| Priority | Action |
|----------|--------|
| **P0** | Remove live credentials from `.env`; use encrypted secret store or OS keyring |
| **P0** | Add `.env` to a pre-commit hook that blocks commits containing credential patterns |
| **P1** | Validate/sanitize category names before passing to API (prevent injection via crafted titles) |
| **P1** | Implement credential rotation support -- `Credentials.from_env()` should support token refresh |
| **P2** | Add audit logging for all edit operations (page title, old hash, new hash, timestamp) |
| **P2** | Rate-limit edit operations independently from API reads (separate `max_edits_per_minute`) |

### DevOps and Testing Recommendations

| Area | Recommendation |
|------|---------------|
| **Test coverage** | Target 80% for `src/`; currently only `text_utils.py` has meaningful tests |
| **Test structure** | Add `tests/conftest.py` with shared `MockMediaWikiPage` and `MockMediaWikiSite` fixtures using the existing Protocols |
| **Test markers** | Use the existing `@pytest.mark.network` marker; ensure all live-API tests are excluded by default |
| **Coverage gaps** | Add tests for: `rate_limiter.py` (all 3 implementations), `config.py` (validation, presets, approval), `types.py` (protocol validation), `wiki_api.py` (all query functions) |
| **Pre-commit hooks** | Add ruff, mypy, and trailing-whitespace checks |
| **Dependency management** | Consolidate into `pyproject.toml` `[project.dependencies]`; remove `requirements.txt` or keep as lockfile |
| **Containerization** | Add `Dockerfile` for reproducible bot execution in CI/cron environments |

---

## Final Evaluation

### Scores

| Metric | Score | Rationale |
|--------|-------|-----------|
| **Overall Project Score** | **6.5 / 10** | Solid foundations with good typing and documentation, but structural issues (monolith, global state) and missing infrastructure (retry, pagination, CI) limit production readiness |
| **Risk Level** | **Medium-High** | Credential exposure, no retry logic, unbounded API responses, and silent failure modes create operational risk |
| **Technical Debt Level** | **Medium** | Global state migration incomplete, dead code present, heavy dependency for trivial use, constants duplicated across modules |
| **Production Readiness** | **40%** | Functional for manual/semi-automated runs with human supervision; not suitable for unattended cron/scheduled operation without the short-term improvements |
| **Test Coverage** | **Low (~25%)** | Only `text_utils.py` and a few edge-case modules have tests; the core 750-line bot module has zero direct tests |

### Recommended Next Steps

1. **Immediately** (this week): Apply the 8 immediate fixes listed above. They are low-risk, high-value cleanup items.
2. **Next sprint** (1-2 weeks): Split the monolithic bot module and add retry logic. These two changes address the highest-impact structural and reliability issues.
3. **Before production deployment**: Implement pagination, add tests for the core bot logic, and set up CI with coverage gates. The bot should not run unattended until retry logic and pagination are in place.
4. **Ongoing**: Migrate credentials to a secret manager, add structured logging, and build integration tests with recorded API responses.

### Component-Level Ratings

| Component | Rating | Key Issue |
|-----------|--------|-----------|
| `src/utils/` | **7.5/10** | Well-designed infrastructure; needs test coverage |
| `src/utils/exceptions.py` | **8.5/10** | Near-perfect exception hierarchy |
| `src/utils/rate_limiter.py` | **7/10** | Three solid implementations; lock-during-sleep issue |
| `src/utils/types.py` | **7/10** | Excellent Protocol design; unused type variables |
| `src/utils/config.py` | **6.5/10** | Good dataclass design; mixes config with state; heavy pywikibot import |
| `src/utils/text_utils.py` | **7.5/10** | Robust bilingual handling; needs regex caching |
| `src/unused_categories_bot.py` | **5/10** | Monolithic, global state, no tests, no retry |
| `src/wiki_api.py` | **6/10** | Clean API layer; unbounded responses; no pagination |
| `src/start.py` | **6/10** | Thin CLI wrapper; duplicates logic from bot module |
| `run.py` | **6.5/10** | Clean entry point; `if setup_logging:` bug |
| `logging_config.py` | **6/10** | Creative color system; undocumented conventions; escapability issue |
| `tests/` | **5/10** | Good pytest config; sparse coverage of core modules |
| Project config | **6/10** | Good tooling config (ruff, black, isort); contradictory Python version targets |

---

*This report was generated through static analysis of all Python source files, configuration files, test infrastructure, and per-module README audits. No dynamic analysis or live API testing was performed.*
