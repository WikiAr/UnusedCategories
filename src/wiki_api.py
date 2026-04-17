"""
Wikipedia API Utilities Module.

This module provides utilities for interacting with the MediaWiki API via mwclient.
It includes functions for fetching category members, interwiki links, and handling
API queries efficiently.

Example:
    Basic usage::

        from wiki_api import get_interwiki_link, sub_cats_query_pages

        # Get interwiki link from a page
        en_title = get_interwiki_link(ar_page, 'en')

        # Get category members with Arabic interwiki links
        members = sub_cats_query_pages(en_site, 'Category:Science')

Notes:
    - All functions handle API errors gracefully and return empty/dict results on failure.
    - Functions are designed to work with mwclient.Site and mwclient.Page objects.
    - Rate limiting should be handled at the site connection level.

"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import mwclient
import mwclient.errors

if TYPE_CHECKING:
    # from collections.abc import Iterator
    from src.utils.types import (  # CategoryTitle,; PageTitle,; MediaWikiSite,; MediaWikiPage,
        LanguageCode,
    )

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

# Default API limits
API_MAX_LIMIT: str = "max"

# Supported namespaces for category queries
NAMESPACE_ARTICLES: str = "0"
NAMESPACE_CATEGORIES: str = "14"
NAMESPACE_ARTICLES_AND_CATEGORIES: str = "0,14"
NAMESPACE_ALL: str = "*"


# =============================================================================
# Category Member Functions
# =============================================================================


def get_category_members(
    site: mwclient.Site,
    category_title: str,
    namespace: int = 0,
) -> list[mwclient.page.Page]:
    """
    Retrieve all members of a specified category from a MediaWiki site.

    This function fetches all pages that belong to a given category, optionally
    filtered by namespace. It uses the MediaWiki API's categorymembers generator.

    Args:
        site: An authenticated mwclient.Site instance connected to the target wiki.
        category_title: The full title of the category (e.g., "Category:Science").
            Can include or omit the namespace prefix.
        namespace: The namespace ID to filter members by. Defaults to 0 (main/article
            namespace). Use 14 for categories, -1 for special pages, etc.
            See: https://www.mediawiki.org/wiki/Manual:Namespace

    Returns:
        A list of mwclient.Page objects representing category members.
        Returns an empty list if:
            - The category doesn't exist
            - The category has no members in the specified namespace
            - An API error occurs

    Raises:
        No exceptions are raised; all errors are logged and result in empty returns.

    Example:
        >>> members = get_category_members(site, "Category:Science", namespace=0)
        >>> for page in members:
        ...     print(page.name)

    Note:
        For categories with many members, this function retrieves all pages,
        which may take significant time and memory. Consider using generators
        for large categories.

    """
    try:
        category = site.pages[category_title]
        # Use list comprehension for efficiency - consumes the generator
        return list(category.members(namespace=namespace))
    except mwclient.errors.APIError as e:
        logger.warning(f"API error getting category members for {category_title}: {e}")
        return []
    except KeyError as e:
        logger.warning(f"Key error in API response for {category_title}: {e}")
        return []


# =============================================================================
# Query Functions
# =============================================================================


def sub_cats_query(
    site: mwclient.Site,
    enlink: str,
    namespace: str = NAMESPACE_ALL,
    lllang: LanguageCode = "ar",
) -> dict[str, str]:
    """
    Query category members with their interwiki links in a single API call.

    This is an optimized function that retrieves category members and their
    language links in one request, reducing the number of API calls needed
    compared to fetching members first then checking each for interwiki links.

    The function uses the MediaWiki API's generator feature with the
    'categorymembers' generator and 'langlinks' prop.

    Args:
        site: An authenticated mwclient.Site instance.
        enlink: The full title of the category to query (e.g., "Category:Science").
        namespace: Comma-separated namespace IDs to include, or "*" for all.
            Defaults to "*" (all namespaces). Common values:
            - "0" for articles only
            - "14" for categories only
            - "0,14" for articles and categories
        lllang: The language code for interwiki links to retrieve.
            Defaults to "ar" (Arabic).

    Returns:
        A dictionary mapping English page titles to their Arabic equivalents.
        - Keys: English page titles (str)
        - Values: Arabic page titles (str)
        Only pages with valid interwiki links are included in the result.

    Example:
        >>> pages = sub_cats_query(en_site, "Category:Science", namespace="0")
        >>> for en_title, ar_title in pages.items():
        ...     if ar_title:
        ...         print(f"{en_title} -> {ar_title}")

    Note:
        This function uses 'max' limits which may be restricted for users
        without the 'apihighlimits' right. Bot accounts typically have this right.

    """
    params: dict[str, str | int] = {
        "action": "query",
        "format": "json",
        "prop": "langlinks",
        "generator": "categorymembers",
        "utf8": 1,
        "formatversion": "2",
        "lllang": lllang,
        "lllimit": API_MAX_LIMIT,
        "gcmtitle": enlink,
        "gcmprop": "title",
        "gcmnamespace": namespace,
        "gcmlimit": API_MAX_LIMIT,
    }

    logger.info(f"<<lightblue>> sub_cats_query: {enlink=}")

    try:
        result = site.api(**params)
    except mwclient.errors.APIError as e:
        logger.warning(f"API error in sub_cats_query for {enlink}: {e}")
        return {}

    query_pages = result.get("query", {}).get("pages", [])

    if not query_pages:
        logger.info(f"<<lightblue>> No pages found for {enlink=}")
        return {}

    # Build a dict of title -> langlink_title (or None if no langlink)
    pages: dict[str, Optional[str]] = {
        page["title"]: next(
            (ll["title"] for ll in page.get("langlinks", []) if ll["lang"] == lllang),
            None,
        )
        for page in query_pages
        if isinstance(page, dict) and "title" in page
    }

    # Filter to only pages with Arabic interwiki links
    pages_with_ar: dict[str, str] = {k: v for k, v in pages.items() if v is not None}

    logger.info(f"<<lightblue>> sub_cats_query: {len(pages)=}, {len(pages_with_ar)=}")

    return pages_with_ar


def sub_cats_query_pages(
    site: mwclient.Site,
    enlink: str,
    namespace: str = NAMESPACE_ALL,
    lllang: LanguageCode = "ar",
) -> dict[mwclient.page.Page, str]:
    """
    Query category members and return Page objects with their interwiki links.

    This is a convenience wrapper around sub_cats_query that converts the
    string-based results to mwclient.Page objects, making it easier to
    work with the pages directly.

    Args:
        site: An authenticated mwclient.Site instance.
        enlink: The full title of the category to query (e.g., "Category:Science").
        namespace: Comma-separated namespace IDs to include, or "*" for all.
            Defaults to "*" (all namespaces).
        lllang: The language code for interwiki links to retrieve.
            Defaults to "ar" (Arabic).

    Returns:
        A dictionary mapping mwclient.Page objects to their Arabic title strings.
        - Keys: mwclient.Page objects for the English pages
        - Values: Arabic page titles (str)

    Example:
        >>> pages = sub_cats_query_pages(en_site, "Category:Science")
        >>> for page, ar_title in pages.items():
        ...     print(f"English: {page.name}, Arabic: {ar_title}")

    Warning:
        The returned Page objects are created lazily and may not exist on the
        wiki. Always check page.exists() before performing operations.

    """
    pages_with_ar = sub_cats_query(site, enlink, namespace, lllang)
    page_objects: dict[mwclient.page.Page, str] = {
        site.pages[title]: lang_title for title, lang_title in pages_with_ar.items()
    }
    return page_objects


# =============================================================================
# Interwiki Link Functions
# =============================================================================


def get_interwiki_link(
    page: mwclient.page.Page,
    target_lang: LanguageCode,
) -> Optional[str]:
    """
    Retrieve the interwiki link from a page to a target language.

    This function fetches the language link (also known as interwiki link)
    from a page to a corresponding page in another language wiki.

    Args:
        page: An mwclient.Page object to get the interwiki link from.
        target_lang: The target language code (e.g., "en" for English,
            "ar" for Arabic, "fr" for French).

    Returns:
        The title of the corresponding page in the target language,
        or None if:
            - No interwiki link exists for the target language
            - An API error occurs
            - The page doesn't exist

    Raises:
        No exceptions are raised; all errors are logged and return None.

    Example:
        >>> en_title = get_interwiki_link(ar_page, "en")
        >>> if en_title:
        ...     print(f"English equivalent: {en_title}")

    Note:
        Interwiki links are stored in the wiki database and are typically
        created by editors using the [[lang:Title]] syntax or through
        Wikidata connections.

    """
    try:
        langlinks = page.langlinks()
        for lang, title in langlinks:
            if lang == target_lang:
                return title
    except mwclient.errors.APIError as e:
        logger.warning(f"API error getting interwiki link for {page.name}: {e}")
    except AttributeError as e:
        logger.warning(f"Attribute error on page object for {page.name}: {e}")

    return None


def get_category_members_pages(
    site: mwclient.Site,
    category_title: str,
    namespace: int = 0,
    lllang: LanguageCode = "ar",
) -> dict[mwclient.page.Page, str]:
    """
    Get category members with their interwiki links (two-step approach).

    This function retrieves category members and then fetches interwiki links
    for each member. This is less efficient than sub_cats_query_pages for large
    categories but may be useful when you need more control over the process.

    Note:
        For most use cases, prefer sub_cats_query_pages() as it makes fewer
        API calls by using the generator API.

    Args:
        site: An authenticated mwclient.Site instance.
        category_title: The full title of the category.
        namespace: The namespace ID to filter by. Defaults to 0 (articles).
        lllang: The target language code for interwiki links. Defaults to "ar".

    Returns:
        A dictionary mapping mwclient.Page objects to their Arabic titles.
        Only includes pages that have Arabic interwiki links.

    Example:
        >>> pages = get_category_members_pages(site, "Category:Science")
        >>> for page, ar_title in pages.items():
        ...     print(f"{page.name} -> {ar_title}")

    """
    members = get_category_members(site, category_title, namespace)
    data: dict[mwclient.page.Page, str] = {}

    for member in members:
        lang_title = get_interwiki_link(member, lllang)
        if lang_title:
            data[site.pages[member.name]] = lang_title

    return data


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Constants
    "API_MAX_LIMIT",
    "NAMESPACE_ARTICLES",
    "NAMESPACE_CATEGORIES",
    "NAMESPACE_ARTICLES_AND_CATEGORIES",
    "NAMESPACE_ALL",
    # Functions
    "get_category_members",
    "sub_cats_query",
    "sub_cats_query_pages",
    "get_interwiki_link",
    "get_category_members_pages",
]
