"""
Text Utilities for Wikipedia Category Processing.

This module provides utilities for working with Wikipedia article text,
particularly focused on category detection and manipulation. It handles
both Arabic (تصنيف) and English (Category) namespace conventions.

The module includes functions for:
- Building regex patterns for category matching
- Detecting categories in article text
- Identifying stub and maintenance categories
- Detecting category redirect templates

Example:
    Basic usage::

        from utils.text_utils import category_in_text, is_ar_stub_or_maintenance_category

        # Check if a category is in article text
        if category_in_text(article_text, "Science"):
            print("Category already present")

        # Check if a category should be skipped
        if is_ar_stub_or_maintenance_category("بذرة علوم"):
            print("Skipping stub category")

Notes:
    - All regex patterns are case-insensitive by default
    - Category patterns support optional sort keys (e.g., [[Category:Science|key]])
    - The module handles both "تصنيف" (Arabic) and "Category" (English) prefixes

"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Final


# Pre-compiled regex pattern for detecting category redirect templates
# Matches: {{تحويل تصنيف|...}} with optional whitespace
_AR_CATEGORY_REDIRECT_PATTERN: Final[re.Pattern[str]] = re.compile(
    r'\{\{\s*تحويل تصنيف\s*\|\s*[^\}]+\}\}'
)


def _build_category_pattern(category_name: str, prefix_pattern: str) -> str:
    """
    Build a regex pattern for matching a category link in wikitext.

    This function creates a regex pattern that matches MediaWiki category links
    with the following features:
    - Handles optional whitespace around colons
    - Supports sort keys (e.g., [[Category:Science|sort key]])
    - Uses re.escape to handle special characters in category names

    Args:
        category_name: The name of the category without the namespace prefix.
            Example: "Science" or "علوم"
        prefix_pattern: Regex pattern for the category namespace prefix.
            Use 'Category' for English-only matching, or
            '(?:تصنيف|Category)' for bilingual matching.

    Returns:
        A regex pattern string (not compiled) for matching the category link.
        The pattern matches the full category link syntax including brackets.

    Example:
        >>> pattern = _build_category_pattern("Science", "Category")
        >>> bool(re.search(pattern, "[[Category:Science]]", re.IGNORECASE))
        True

        >>> pattern = _build_category_pattern("علوم", "(?:تصنيف|Category)")
        >>> bool(re.search(pattern, "[[تصنيف:علوم]]", re.IGNORECASE))
        True

    Note:
        The returned pattern should be used with re.IGNORECASE for proper
        matching of the "Category" prefix in English.

    """
    return (
        r'\[\[\s*' + prefix_pattern + r'\s*:\s*' +
        re.escape(category_name) + r'\s*(?:\|[^\]]*?)?\]\]'
    )


def category_in_text(text: str, category_name: str) -> bool:
    """
    Check if a category link is present in article wikitext.

    This function searches for category links in both Arabic (تصنيف) and
    English (Category) namespace formats. It handles variations in spacing
    and the presence of sort keys.

    Args:
        text: The full wikitext of a Wikipedia article.
        category_name: The category name to search for, without namespace prefix.
            Example: "Science" or "علوم"

    Returns:
        True if a matching category link is found in the text, False otherwise.
        The search is case-insensitive for the namespace prefix.

    Example:
        >>> text = "Article content\\n[[تصنيف:علوم]]"
        >>> category_in_text(text, "علوم")
        True

        >>> text = "[[Category:Science|sort key]]"
        >>> category_in_text(text, "Science")
        True

        >>> category_in_text("No categories here", "Science")
        False

    Note:
        This function only matches actual category links ([[Category:...]]),
        not category names mentioned in regular article text.

    """
    # Match [[تصنيف:...]] or [[Category:...]]
    pattern = _build_category_pattern(category_name, '(?:تصنيف|Category)')
    return bool(re.search(pattern, text, re.IGNORECASE))


def en_page_has_category_in_text(
    text: str,
    category_target: str,
    page_title: str = "",
) -> bool:
    """
    Check if an English Wikipedia page contains a category directly in its wikitext.

    This function is specifically designed for English Wikipedia and includes
    special handling for category pages that use the {{Title year range}} template.
    This template generates year ranges dynamically, so we need to expand it
    for proper matching.

    Args:
        text: The full wikitext of the English Wikipedia page.
        category_target: The category name to search for, with or without
            the "Category:" prefix. Example: "Category:Science" or "Science"
        page_title: The title of the page being checked. Used for special
            handling of category pages with year range templates.
            Example: "Category:1951–52 in North American football by country"

    Returns:
        True if the category is found directly in the page source text,
        False otherwise. This distinguishes between categories added directly
        vs. those added via templates.

    Example:
        >>> text = "Article text\\n[[Category:History]]"
        >>> en_page_has_category_in_text(text, "History")
        True

        >>> en_page_has_category_in_text(text, "Category:History")
        True

    Special Cases:
        For category pages containing {{Title year range}}, the function
        extracts year patterns from the category_target and substitutes
        them into the text for matching:

        >>> text = "[[Category:{{Title year range}} in Science]]"
        >>> en_page_has_category_in_text(text, "Category:1951 in Science", "Category:1951 test")
        True

    Note:
        This function is used to determine if a category was added directly
        to a page versus being added via a template. Categories added via
        templates should typically be skipped when processing unused categories.

    """
    # Special handling for category pages with year range templates
    if page_title.startswith("Category:") and "{{Title year range}}" in text:
        # Extract year pattern from the target category name
        # Matches: "1951–52", "1951-1952", "1951-", or single years
        match_pattern = r'(\d\d\d\d–\d\d\d?\d?|\d+[–-]\d+|\d+)'
        if match := re.search(match_pattern, category_target):
            # Replace the template with the actual year for matching
            # Note: flags= keyword argument is required, not positional
            text = re.sub(
                r'\{\{Title year range\}\}',
                match.group(1),
                text,
                flags=re.IGNORECASE
            )

    # Remove prefix if present for matching
    if ':' in category_target:
        cat_name_without_prefix = category_target.split(':', 1)[1]
    else:
        cat_name_without_prefix = category_target

    # Match [[Category:...]] with optional sort key
    pattern = _build_category_pattern(cat_name_without_prefix, 'Category')
    return bool(re.search(pattern, text, re.IGNORECASE))


def is_ar_stub_or_maintenance_category(category_name: str) -> bool:
    """
    Determine if an Arabic category is a stub or maintenance category.

    Stub and maintenance categories are typically administrative and should
    be skipped when processing unused categories, as they serve special
    purposes on the wiki.

    The function checks for:
    - Categories starting with "بذرة" (stub, singular)
    - Categories containing "بذور" (stubs, plural)
    - Categories containing "صيانة" (maintenance)

    Args:
        category_name: The category name with or without the "تصنيف:" prefix.
            Examples: "بذرة علوم", "تصنيف:بذور الرياضيات", "صيانة ويكيبيديا"

    Returns:
        True if the category is identified as a stub or maintenance category,
        False otherwise.

    Example:
        >>> is_ar_stub_or_maintenance_category("بذرة علوم")
        True
        >>> is_ar_stub_or_maintenance_category("تصنيف:بذور الرياضيات")
        True
        >>> is_ar_stub_or_maintenance_category("صيانة المقالات")
        True
        >>> is_ar_stub_or_maintenance_category("علوم")
        False

    Note:
        - "بذرة" is checked at the start only (startswith)
        - "بذور" and "صيانة" are checked anywhere in the name (in operator)

    """
    # Remove prefix if present
    if ':' in category_name:
        category_name = category_name.split(':', 1)[1]

    # Check if category name starts with "بذرة" (stub, singular)
    if category_name.startswith('بذرة'):
        return True

    # Check for stub-related terms (بذور = stubs, plural)
    if 'بذور' in category_name:
        return True

    # Check for maintenance-related terms (صيانة = maintenance)
    if 'صيانة' in category_name:
        return True

    return False


def is_en_stub_or_maintenance_category(category_name: str) -> bool:
    """
    Determine if an English category is a stub or maintenance category.

    This is the English equivalent of is_ar_stub_or_maintenance_category,
    checking for English stub and maintenance category naming patterns.

    The function checks for:
    - Categories containing "stub" (case-insensitive)
    - Categories containing "maintenance" (case-insensitive)

    Args:
        category_name: The category name with or without the "Category:" prefix.
            Examples: "Science stubs", "Category:Wikipedia maintenance"

    Returns:
        True if the category is identified as a stub or maintenance category,
        False otherwise.

    Example:
        >>> is_en_stub_or_maintenance_category("Science stubs")
        True
        >>> is_en_stub_or_maintenance_category("Category:WIKIPEDIA MAINTENANCE")
        True
        >>> is_en_stub_or_maintenance_category("Science")
        False

    Warning:
        This function uses substring matching, so a category like "Stubborn articles"
        would incorrectly match. This is a known limitation but acceptable for
        typical Wikipedia category naming conventions.

    """
    # Remove prefix if present
    if ':' in category_name:
        category_name = category_name.split(':', 1)[1]

    # Convert to lowercase for case-insensitive matching
    category_name_lower = category_name.lower()

    # Check for stub-related terms
    if 'stub' in category_name_lower:
        return True

    # Check for maintenance-related terms
    if 'maintenance' in category_name_lower:
        return True

    return False


def has_ar_category_redirect_template(text: str) -> bool:
    """
    Check if Arabic article wikitext contains a category redirect template.

    The category redirect template (تحويل تصنيف) is used on Arabic Wikipedia
    to indicate that a category has been moved/redirected. Articles with
    this template should typically be skipped when adding categories.

    Template syntax: {{تحويل تصنيف|old_category|new_category}}

    Args:
        text: The full wikitext of an Arabic Wikipedia article or category page.

    Returns:
        True if the category redirect template is found, False otherwise.

    Example:
        >>> text = "{{تحويل تصنيف|تصنيف قديم|تصنيف جديد}}"
        >>> has_ar_category_redirect_template(text)
        True

        >>> text = "Regular article without redirect template"
        >>> has_ar_category_redirect_template(text)
        False

    Note:
        The function matches the template with flexible whitespace:
        - {{تحويل تصنيف|...}}
        - {{  تحويل تصنيف  |  ...  }}

    """
    return bool(_AR_CATEGORY_REDIRECT_PATTERN.search(text))


__all__ = [
    "_build_category_pattern",
    "category_in_text",
    "en_page_has_category_in_text",
    "is_ar_stub_or_maintenance_category",
    "is_en_stub_or_maintenance_category",
    "has_ar_category_redirect_template",
]
