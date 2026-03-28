#!/usr/bin/env python3
"""
Unused Categories Bot for Arabic Wikipedia.

This bot processes unused categories on Arabic Wikipedia by:
1. Fetching unused categories from Arabic Wikipedia's Special:UnusedCategories
2. Finding corresponding categories on English Wikipedia via interwiki links
3. Getting members of the English categories
4. Finding Arabic equivalents of those articles
5. Adding the Arabic category to articles that don't have it

Usage:
    python unused_categories_bot.py           # Process all unused categories
    python unused_categories_bot.py ask       # Interactive confirmation mode
    python unused_categories_bot.py -cat:CategoryName  # Process specific category

Environment Variables:
    WIKIPEDIA_BOT_USERNAME: Wikipedia bot account username
    WIKIPEDIA_BOT_PASSWORD: Wikipedia bot account password

Example:
    Run with interactive confirmation::

        $ python unused_categories_bot.py ask

    Process a specific category::

        $ python unused_categories_bot.py -cat:تصنيف:أفلام_مغامرات_سويسرية

Notes:
    - Requires a Wikipedia bot account with appropriate permissions
    - Bot edits should comply with Wikipedia's bot policy
    - Use 'ask' mode for testing and review before automated runs

"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, Final, Optional

import mwclient
import mwclient.errors
from dotenv import load_dotenv

from wiki_api import sub_cats_query_pages, get_interwiki_link
from utils import (
    showDiff,
    logger,
    en_page_has_category_in_text,
    category_in_text,
    is_ar_stub_or_maintenance_category,
    is_en_stub_or_maintenance_category,
    has_ar_category_redirect_template,
)
from utils.config import (
    BotConfig,
    Credentials,
    ApprovalDecision,
    DEFAULT_CATEGORY_LIMIT,
)
from utils.exceptions import (
    BotError,
    CredentialError,
    CategoryProcessingError,
    PageProcessingError,
    EditError,
    APIError,
)
from utils.rate_limiter import SimpleRateLimiter

if TYPE_CHECKING:
    from utils.types import CategoryTitle, PageTitle


# Initialize environment
load_dotenv()


# =============================================================================
# Constants
# =============================================================================

# Edit summary for adding categories (Arabic)
EDIT_SUMMARY: Final[str] = "بوت: أضاف 1 تصنيف"

# Default limit for fetching unused categories
DEFAULT_LIMIT: Final[int] = DEFAULT_CATEGORY_LIMIT


# =============================================================================
# Global Configuration (for backwards compatibility with tests)
# =============================================================================

# Global config instance - will be replaced by parameter passing
_config: Optional[BotConfig] = None

# Legacy global state (deprecated - use BotConfig instead)
_ask_mode: bool = False
_auto_approve_all: bool = False


def _get_config() -> BotConfig:
    """Get or create the global config instance."""
    global _config
    if _config is None:
        _config = BotConfig()
    return _config


def set_ask_mode(enabled: bool) -> None:
    """
    Enable or disable interactive confirmation mode.

    .. deprecated::
        Use BotConfig.ask_mode instead.

    In ask mode, the bot prompts for confirmation before each edit,
    allowing for human review of changes.

    Args:
        enabled: True to enable ask mode, False to disable.

    Example:
        >>> set_ask_mode(True)  # Enable interactive mode
        >>> set_ask_mode(False)  # Disable for automated operation

    """
    global _ask_mode, _config
    _ask_mode = enabled
    if _config is not None:
        _config.ask_mode = enabled
    else:
        _config = BotConfig(ask_mode=enabled)


def is_ask_mode() -> bool:
    """
    Check if interactive confirmation mode is enabled.

    .. deprecated::
        Use BotConfig.ask_mode instead.

    Returns:
        True if ask mode is enabled, False otherwise.

    """
    return _ask_mode or _get_config().ask_mode


# =============================================================================
# Approval Functions
# =============================================================================

def confirm_edit(page_title: str, old_text: str, new_text: str) -> bool:
    """
    Request user confirmation for an edit in interactive mode.

    Shows the target page title, a colorized diff of the changes, and
    prompts for user input. Supports single-edit approval and bulk
    approval of all remaining edits.

    Args:
        page_title: Title of the page being edited.
        old_text: Original page text before the edit.
        new_text: New page text after the proposed edit.

    Returns:
        True if the edit should proceed, False to skip this edit.

    User Input Options:
        - 'y' or 'yes' or Enter: Approve this edit
        - 'n' or 'no': Skip this edit
        - 'a' or 'all': Approve this and all remaining edits

    Example:
        >>> if confirm_edit("Test Page", "old", "new"):
        ...     page.save(new_text, summary="Bot edit")

    """
    global _auto_approve_all

    config = _get_config()

    # Auto-approve is enabled - skip all confirmations
    if _auto_approve_all or config.auto_approve_all:
        return True

    # Not in ask mode - proceed without confirmation
    if not config.ask_mode and not _ask_mode:
        return True

    # Display target page
    logger.info(f"\n{'='*60}")
    logger.info(f"Target: {page_title}")
    logger.info(f"{'='*60}")

    # Display the diff
    showDiff(old_text, new_text)
    logger.info(f"{'='*60}")

    # Prompt for confirmation
    logger.info(
        f"<<green>> Target: {page_title}, "
        f"Options: [y]es / [n]o / [a]ll (approve all remaining)"
    )

    try:
        response = input("Confirm edit? [Y/n/a]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        logger.warning("Input interrupted, skipping edit.")
        return False

    # Empty response or "y"/"yes" means proceed with this edit
    if response in ('', 'y', 'yes'):
        return True

    # "a" means approve all remaining edits
    if response == 'a':
        _auto_approve_all = True
        config.auto_approve_all = True
        logger.info("Auto-approving all remaining edits.")
        return True

    # Any other response means skip
    logger.error_red("Edit skipped.")
    return False


# =============================================================================
# Category Analysis Functions
# =============================================================================

def is_hidden_category(category_page: mwclient.page.Page) -> bool:
    """
    Check if a category is a hidden category on Wikipedia.

    Hidden categories are typically used for maintenance and tracking
    purposes and are not displayed to regular readers. They are marked
    with the __HIDDENCAT__ magic word.

    Args:
        category_page: mwclient.Page object representing the category.

    Returns:
        True if the category is hidden, False otherwise.

    Note:
        This function queries the MediaWiki API for categoryinfo,
        which includes the 'hidden' property.

    """
    try:
        result = category_page.site.get(
            'query',
            prop='categoryinfo',
            titles=category_page.name
        )

        if 'query' in result and 'pages' in result['query']:
            pages = result['query']['pages']
            for page_id, page_data in pages.items():
                if 'categoryinfo' in page_data:
                    return page_data['categoryinfo'].get('hidden', False)
    except mwclient.errors.APIError as e:
        logger.warning(
            f"API error checking hidden category for {category_page.name}: {e}"
        )
    except KeyError as e:
        logger.warning(
            f"Unexpected API response structure for {category_page.name}: {e}"
        )

    return False


def should_skip_ar_category(category_page: mwclient.page.Page) -> bool:
    """
    Determine if an Arabic category should be skipped during processing.

    Categories are skipped if they are:
    - Hidden categories (marked with __HIDDENCAT__)
    - Maintenance categories (contain "صيانة")
    - Stub categories (start with "بذرة" or contain "بذور")

    Args:
        category_page: mwclient.Page object of the Arabic category.

    Returns:
        True if the category should be skipped, False to process it.

    """
    # Check if hidden
    if is_hidden_category(category_page):
        logger.info(f"  Skipping hidden category: {category_page.name}")
        return True

    # Check if stub or maintenance category
    if is_ar_stub_or_maintenance_category(category_page.name):
        logger.info(
            f"  Skipping stub/maintenance category: {category_page.name}"
        )
        return True

    return False


def should_skip_en_category(category_page: mwclient.page.Page) -> bool:
    """
    Determine if an English category should be skipped during processing.

    Categories are skipped if they are:
    - Hidden categories (marked with __HIDDENCAT__)
    - Maintenance categories (contain "maintenance")
    - Stub categories (contain "stub")

    Args:
        category_page: mwclient.Page object of the English category.

    Returns:
        True if the category should be skipped, False to process it.

    """
    # Check if hidden
    if is_hidden_category(category_page):
        logger.info(f"  Skipping hidden English category: {category_page.name}")
        return True

    # Check if stub or maintenance category
    if is_en_stub_or_maintenance_category(category_page.name):
        logger.info(
            f"  Skipping stub/maintenance English category: {category_page.name}"
        )
        return True

    return False


# =============================================================================
# Page Analysis Functions
# =============================================================================

def is_redirect_page(page: mwclient.page.Page) -> bool:
    """
    Check if a page is a redirect page.

    Redirect pages should be skipped when adding categories, as the
    category should be added to the target page instead.

    Args:
        page: mwclient.Page object to check.

    Returns:
        True if the page is a redirect, False otherwise.

    """
    try:
        return page.redirects_to() is not None
    except mwclient.errors.APIError as e:
        logger.warning(f"API error checking redirect status for {page.name}: {e}")
        return False
    except AttributeError as e:
        logger.warning(f"Attribute error checking redirect for {page.name}: {e}")
        return False


# =============================================================================
# Connection Functions
# =============================================================================

def load_credentials() -> tuple[str, str]:
    """
    Load Wikipedia credentials from environment variables.

    The credentials should be set in the environment or a .env file:
    - WIKIPEDIA_BOT_USERNAME: The bot account username
    - WIKIPEDIA_BOT_PASSWORD: The bot account password

    Returns:
        A tuple of (username, password).

    Raises:
        CredentialError: If credentials are not found in environment variables.

    Example:
        >>> username, password = load_credentials()
        >>> site.login(username, password)

    """
    try:
        creds = Credentials.from_env()
        return creds.username, creds.password
    except CredentialError:
        raise CredentialError(
            "Credentials not found. Please set WIKIPEDIA_BOT_USERNAME and "
            "WIKIPEDIA_BOT_PASSWORD environment variables."
        )


def connect_to_wikipedia(
    site_url: str,
    username: str,
    password: str,
    rate_limiter: Optional[SimpleRateLimiter] = None,
) -> mwclient.Site:
    """
    Connect and authenticate to a Wikipedia site.

    Creates an HTTPS connection to the specified Wikipedia site and
    authenticates using the provided credentials.

    Args:
        site_url: Wikipedia site URL (e.g., 'ar.wikipedia.org').
        username: Wikipedia bot account username.
        password: Wikipedia bot account password.
        rate_limiter: Optional rate limiter for API calls.

    Returns:
        An authenticated mwclient.Site object.

    Raises:
        mwclient.errors.LoginError: If authentication fails.
        mwclient.errors.APIError: If there's an API connection error.

    Example:
        >>> site = connect_to_wikipedia('ar.wikipedia.org', 'user', 'pass')
        >>> print(site.site['name'])

    """
    site = mwclient.Site(site_url, scheme='https')
    site.login(username, password)
    logger.info(f"Successfully connected to {site_url}")
    return site


# =============================================================================
# Category Retrieval Functions
# =============================================================================

def get_unused_categories(
    site: mwclient.Site,
    limit: int = DEFAULT_LIMIT,
    rate_limiter: Optional[SimpleRateLimiter] = None,
) -> list[str]:
    """
    Fetch unused categories from Wikipedia.

    Uses the MediaWiki API's querypage module to retrieve the list of
    unused categories from Special:UnusedCategories.

    Args:
        site: An authenticated mwclient.Site object.
        limit: Maximum number of categories to fetch. Defaults to 1000.
        rate_limiter: Optional rate limiter for API calls.

    Returns:
        A list of category titles (strings) including the "تصنيف:" prefix.

    Example:
        >>> categories = get_unused_categories(ar_site, limit=100)
        >>> for cat in categories:
        ...     print(cat)

    Note:
        The API may return fewer categories than requested if there
        aren't enough unused categories on the wiki.

    """
    logger.info(f"Fetching up to {limit} unused categories...")

    categories: list[str] = []

    try:
        # Apply rate limiting if available
        if rate_limiter:
            with rate_limiter:
                result = site.get(
                    'query',
                    list='querypage',
                    qppage='Unusedcategories',
                    qplimit=limit
                )
        else:
            result = site.get(
                'query',
                list='querypage',
                qppage='Unusedcategories',
                qplimit=limit
            )

        if 'query' in result and 'querypage' in result['query']:
            querypage_data = result['query']['querypage']
            if 'results' in querypage_data:
                raw_categories = querypage_data['results']
                categories = [cat['title'] for cat in raw_categories]
    except mwclient.errors.APIError as e:
        logger.warning(f"API error fetching unused categories: {e}")

    logger.info(f"Found {len(categories)} unused categories")
    return categories


# =============================================================================
# Edit Functions
# =============================================================================

def add_category_to_page(
    page: mwclient.page.Page,
    category_name: str,
    summary: str,
    config: Optional[BotConfig] = None,
    dry_run: bool = False,
) -> bool:
    """
    Add a category to a Wikipedia page if it's not already present.

    This function performs several checks before adding:
    1. Skips redirect pages
    2. Skips pages with category redirect templates
    3. Skips pages that already have the category
    4. In ask mode, requests user confirmation

    Args:
        page: mwclient.Page object to edit.
        category_name: Name of the category without namespace prefix
            (e.g., "علوم" not "تصنيف:علوم").
        summary: Edit summary for the change.
        config: Optional BotConfig for approval workflow.
        dry_run: If True, don't actually save the edit.

    Returns:
        True if the category was added successfully, False otherwise
        (including cases where the category already existed or was skipped).

    """
    # Use provided config or get global
    if config is None:
        config = _get_config()

    # Skip redirect pages
    if is_redirect_page(page):
        return False

    try:
        text = page.text()
    except mwclient.errors.APIError as e:
        logger.warning(f"Could not fetch text for {page.name}: {e}")
        return False

    # Skip pages with category redirect templates
    if has_ar_category_redirect_template(text):
        return False

    # Check if category already exists
    if category_in_text(text, category_name):
        return False

    # Add category at the end of the text
    new_text = text.rstrip() + f"\n[[تصنيف:{category_name}]]"

    # Check edit limits
    if not config.can_edit:
        logger.info(f"Edit limit reached, skipping {page.name}")
        return False

    # Ask for confirmation if in ask mode
    if not confirm_edit(page.name, text, new_text):
        return False

    # Dry run mode - don't actually save
    if dry_run or config.dry_run:
        logger.info(f"[DRY RUN] Would add category to {page.name}")
        return True

    # Save the page
    try:
        result = page.save(new_text, summary=summary)
        config.record_edit()
        return bool(result)
    except mwclient.errors.APIError as e:
        logger.error(f"Failed to save {page.name}: {e}")
        return False


# =============================================================================
# Category Processing Functions
# =============================================================================

def process_category(
    ar_site: mwclient.Site,
    en_site: mwclient.Site,
    category_name: str,
    config: Optional[BotConfig] = None,
    rate_limiter: Optional[SimpleRateLimiter] = None,
) -> int:
    """
    Process a single unused category from Arabic Wikipedia.

    This is the main processing function that:
    1. Validates the Arabic category (not hidden/stub/maintenance)
    2. Finds the English equivalent via interwiki links
    3. Validates the English category
    4. Gets members of the English category with Arabic interwiki links
    5. Adds the Arabic category to corresponding Arabic articles

    Args:
        ar_site: Authenticated Arabic Wikipedia site object.
        en_site: Authenticated English Wikipedia site object.
        category_name: Name of the category (may include "تصنيف:" prefix).
        config: Optional BotConfig for configuration.
        rate_limiter: Optional rate limiter for API calls.

    Returns:
        The number of categories successfully added to pages.

    """
    if config is None:
        config = _get_config()

    # Extract category name without prefix
    if ':' in category_name:
        category_name_without_prefix = category_name.split(':', 1)[1]
    else:
        category_name_without_prefix = category_name

    logger.info(f"\n{'='*60}")
    logger.info(f"<<yellow>> Processing: {category_name}")
    logger.info(f"{'='*60}")

    # Get the Arabic category page object
    ar_category_page = ar_site.pages[category_name]

    # Check if Arabic category should be skipped
    if should_skip_ar_category(ar_category_page):
        return 0

    # Get English Wikipedia interwiki link
    en_category_title = get_interwiki_link(ar_category_page, 'en')

    if not en_category_title:
        logger.info(f"No English Wikipedia link found for {category_name}")
        return 0

    logger.info(f"English Wikipedia category: {en_category_title}")

    # Get the English category page object
    en_category_page = en_site.pages[en_category_title]

    # Check if English category should be skipped
    if should_skip_en_category(en_category_page):
        return 0

    # Get members of the English category with Arabic interwiki links
    # Namespace "0,14" = articles + categories
    en_members = sub_cats_query_pages(en_site, en_category_title, namespace="0,14")

    if not en_members:
        logger.info(f"No members found in English category {en_category_title}")
        return 0

    logger.info(
        f"Found {len(en_members)} members in English category: {en_category_title}"
    )

    # Process each member
    added_count = 0

    for n, (en_member, ar_title) in enumerate(en_members.items(), start=1):
        # Check edit limits
        if not config.can_edit:
            logger.info(f"Edit limit reached, stopping processing")
            break

        logger.info(
            f"<<purple>> Processing member {n}/{len(en_members)}: {en_member.name}"
        )

        # Get page properties
        en_page_title = en_member.name
        namespace = en_member.namespace

        try:
            text = en_member.text()
        except mwclient.errors.APIError as e:
            logger.warning(f"Could not fetch text for {en_page_title}: {e}")
            continue

        # Check if the English page contains the category directly in its text
        # (not added via a template)
        category_in_text_result = en_page_has_category_in_text(
            text, en_category_title, en_page_title
        )

        # Skip if category not in text (possibly added via template)
        # Exception: category pages (namespace 14) may have dynamic categories
        if not category_in_text_result and namespace != 14:
            logger.info(
                f"  Skipping {en_page_title}: "
                f"category not in text (possibly added via template)"
            )
            continue

        # Check if Arabic interwiki link exists
        if not ar_title:
            logger.info(f"No Arabic Wikipedia link found for {en_page_title}")
            continue

        logger.info(f"Checking Arabic article: {ar_title}/{en_page_title}")

        # Get Arabic article page
        ar_article = ar_site.pages[ar_title]

        # Add category if not present
        if add_category_to_page(
            ar_article,
            category_name_without_prefix,
            config.edit_summary or EDIT_SUMMARY,
            config=config,
        ):
            logger.info(f"<<green>>    ✓ Added category to {ar_title}")
            added_count += 1
        else:
            logger.info(f"    - Category already exists in {ar_title}")

    logger.info(f"Total categories added: {added_count}")
    return added_count


# =============================================================================
# Argument Parsing Functions
# =============================================================================

def parse_category_args() -> list[str]:
    """
    Parse command-line arguments for specific categories.

    Looks for arguments in the format -cat:CategoryName and extracts
    the category names. Underscores in the argument are replaced with spaces.

    Returns:
        A list of category names specified on the command line.

    Example:
        Command line: python bot.py -cat:تصنيف:علوم -cat:Category:Science
        Returns: ["تصنيف:علوم", "Category:Science"]

    """
    categories: list[str] = []

    for arg in sys.argv:
        arg_key, _, value = arg.partition(":")
        if arg_key == "-cat" and value:
            # Replace underscores with spaces for wiki compatibility
            categories.append(value.replace("_", " "))

    return categories


# =============================================================================
# Main Entry Point
# =============================================================================

def main() -> None:
    """
    Main entry point for the Unused Categories Bot.

    This function:
    1. Parses command-line arguments for mode and category selection
    2. Loads credentials and connects to Wikipedia sites
    3. Fetches unused categories (or uses specified categories)
    4. Processes each category to add it to relevant articles

    Command-line Usage:
        python unused_categories_bot.py           # Process all unused categories
        python unused_categories_bot.py ask       # Interactive confirmation mode
        python unused_categories_bot.py -cat:Cat  # Process specific category

    """
    global _config

    # Check for "ask" argument to enable interactive confirmation mode
    if 'ask' in sys.argv:
        set_ask_mode(True)
        logger.info("Interactive confirmation mode enabled.")

    # Initialize config
    config = _get_config()
    logger.set_level(config.log_level.value)

    logger.info("Starting Unused Categories Bot for Arabic Wikipedia")
    logger.info("=" * 60)

    # Load credentials
    try:
        username, password = load_credentials()
    except CredentialError as e:
        logger.error_red(str(e))
        sys.exit(1)

    # Create rate limiter
    rate_limiter = SimpleRateLimiter(calls_per_second=config.rate_limit)

    # Connect to Arabic and English Wikipedia
    try:
        ar_site = connect_to_wikipedia(
            'ar.wikipedia.org',
            username,
            password,
            rate_limiter=rate_limiter
        )
        en_site = connect_to_wikipedia(
            'en.wikipedia.org',
            username,
            password,
            rate_limiter=rate_limiter
        )
    except mwclient.errors.LoginError as e:
        logger.error_red(f"Login failed: {e}")
        sys.exit(1)
    except mwclient.errors.APIError as e:
        logger.error_red(f"Connection error: {e}")
        sys.exit(1)

    # Get categories to process
    unused_categories = parse_category_args()

    if not unused_categories:
        # Fetch unused categories from Arabic Wikipedia
        unused_categories = get_unused_categories(
            ar_site,
            limit=config.category_limit,
            rate_limiter=rate_limiter
        )

    if not unused_categories:
        logger.info("No unused categories found")
        return

    # Process each category
    total_added = 0
    for category in unused_categories:
        try:
            added = process_category(
                ar_site,
                en_site,
                category,
                config=config,
                rate_limiter=rate_limiter
            )
            total_added += added
        except BotError as e:
            logger.error(f"Bot error processing category {category}: {e}")
        except Exception as e:
            # Log unexpected exceptions but continue processing
            logger.exception(f"Unexpected error processing category {category}: {e}")

    # Print statistics
    logger.info("\n" + "=" * 60)
    logger.info(f"Bot execution completed. Total categories added: {total_added}")
    logger.info(f"Total edits made: {config.edits_made}")
    if rate_limiter:
        stats = rate_limiter.get_stats()
        logger.info(f"Rate limiter stats: {stats}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
