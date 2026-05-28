# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python bot that populates unused categories on Arabic Wikipedia. It fetches unused Arabic categories, finds their English equivalents via interwiki links, gets members of those English categories, locates the Arabic versions of those articles, then adds the category to articles that lack it.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot (all unused categories)
python run.py

# Run with interactive confirmation mode
python run.py ask

# Run with specific category
python run.py -cat:CategoryName

# Debug mode (extra verbose logging)
python run.py debug

# Run tests (network tests excluded by default)
python -m pytest

# Run tests including network tests
python -m pytest -m all

# Run a single test file
python -m pytest tests/test_utils.py

# Run a single test function
python -m pytest tests/test_utils.py::test_function_name

# Run tests with coverage
python -m pytest --cov=src --cov-report=term-missing
```

## Architecture

```
run.py                          Entry point: loads env/logging, calls src.main_entry()
  └─ src/__init__.py            Re-exports main_entry
    └─ src/start.py             CLI arg parsing (ask mode, -cat:Name), calls start_work()
      └─ src/unused_categories_bot.py   Core bot logic:
            - connect_to_wikipedia() via mwclient
            - get_unused_categories() from Special:UnusedCategories
            - process_category(): validates AR cat → finds EN cat via interwiki →
              gets EN members with AR interwiki → adds AR category to AR articles
            - add_category_to_page(): checks redirects, existing cats, ask mode, then saves
          └─ src/wiki_api.py           MediaWiki API wrappers (mwclient-based):
              - sub_cats_query_pages(): category members + interwiki links in one API call
              - get_interwiki_link(): language link lookup
          └─ src/utils/
              - config.py        BotConfig dataclass, Credentials, ApprovalDecision enum
              - text_utils.py    Category regex matching (both [[تصنيف:X]] and [[Category:X]])
              - rate_limiter.py  SimpleRateLimiter, TokenBucketRateLimiter, AdaptiveRateLimiter
              - exceptions.py    BotError hierarchy (CredentialError, APIError, etc.)
              - types.py         TypedDict/Protocol definitions for MediaWiki API responses
```

## Key Design Decisions

- **Two-site model**: The bot connects to both Arabic (`ar.wikipedia.org`) and English (`en.wikipedia.org`) Wikipedia. English categories serve as the source of truth for finding articles to categorize.
- **Interwiki-based discovery**: Instead of directly searching Arabic Wikipedia, the bot uses English category members and follows interwiki links back to Arabic articles. This leverages the typically more complete English category structure.
- **Category-in-text check**: The bot only adds categories when the English page has the category explicitly in its wikitext (not via template). This avoids incorrectly propagating template-based categories.
- **Namespace "0,14"**: Category member queries include both articles (ns 0) and subcategories (ns 14).
- **Category prefix handling**: Category names may arrive with or without the `تصنيف:` prefix. Functions handle both forms, stripping the prefix internally when needed.

## Code Conventions

- **Line length**: 120 characters (Black/Ruff/isort all configured for this)
- **Python target**: 3.13
- **Formatting**: Black for code formatting, isort (profile "black") for imports, Ruff for linting
- **Lint ignores**: E402, E225, E226, E227, E228, E252, E501, F841, E224, E203, F401
- **f-strings**: Use f-strings (flynt configured). The logging system supports color tags like `<<green>>` and `<<red>>` in log messages.
- **Type annotations**: Use `from __future__ import annotations` at the top of files. Type aliases like `LanguageCode`, `CategoryTitle`, `PageTitle` are defined in `src/utils/types.py`.
- **Docstrings**: Use Google-style with Args/Returns/Raises sections.
- **Edit summary**: Bot edits use the Arabic summary `"بوت: أضاف 1 تصنيف"`.

## Environment Variables

Required (set in `.env`, see `example.env`):
- `WIKIPEDIA_BOT_USERNAME` — Bot account username
- `WIKIPEDIA_BOT_PASSWORD` — Bot password (from Special:BotPasswords)

Optional:
- `WIKI_BOT_ASK_MODE` — Set to `true` for interactive mode
- `WIKI_BOT_DRY_RUN` — Set to `true` for simulation mode
- `WIKI_BOT_CATEGORY_LIMIT` — Max categories to process (default: 1000)
- `WIKI_BOT_RATE_LIMIT` — API calls per second (default: 10.0)

## Testing

- Tests live in `tests/` with pytest. The `pytest.ini` configures `pythonpath = .` for imports.
- Default pytest run excludes `network` marker tests (`-m "not network"`).
- Available markers: `all`, `fast`, `unit`, `network`, `integration`.
- Coverage is measured on `src/` with branch coverage enabled.
- The bot interacts with live Wikipedia — be cautious when testing changes that affect API calls or page edits. Use `ask` mode or `dry_run` for manual testing.

## Deployment

On push to `main`, GitHub Actions deploys to Wikimedia Toolforge via SCP + SSH (see `.github/workflows/update.yml`). The CI workflow (`pytest.yaml`) runs pytest on pull requests.
