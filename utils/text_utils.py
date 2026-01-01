import re


def _build_category_pattern(category_name, prefix_pattern):
    """
    Build a regex pattern for matching a category in text.

    Args:
        category_name: Name of the category (without prefix)
        prefix_pattern: Regex pattern for the category prefix (e.g., 'Category' or '(?:تصنيف|Category)')

    Returns:
        str: Regex pattern for matching the category
    """
    return r'\[\[\s*' + prefix_pattern + r'\s*:\s*' + re.escape(category_name) + r'\s*(?:\|[^\]]*?)?\]\]'


def category_in_text(text, category_name):
    """
    Check if a category is already in the article text.

    Args:
        text: Article text
        category_name: Name of the category (without "Category:" prefix)

    Returns:
        bool: True if category is found in text, False otherwise
    """
    # Match [[تصنيف:...]] or [[Category:...]]
    pattern = _build_category_pattern(category_name, '(?:تصنيف|Category)')
    return bool(re.search(pattern, text, re.IGNORECASE))


def en_page_has_category_in_text(text, category_target, page_title: str = "") -> bool:
    """
    Check if an English page contains the category directly in its text.

    This ensures the category is actually in the article text and not
    added via a template.

    Args:
        text: mwclient.Page object text
        category_target: Name of the category (with or without "Category:" prefix)

    Returns:
        bool: True if category is found in page text, False otherwise
    """
    if page_title.startswith("Category:") and "{{Title year range}}" in text:
        # Special case: skip checking category pages with year range templates
        # return True
        match_pattern = r'(\d\d\d\d–\d\d\d?\d?|\d+[–-]\d+|\d+)'
        if m := re.search(match_pattern, category_target):
            text = re.sub(r'\{\{Title year range\}\}', m.group(1), text, re.I)

    # Remove prefix if present for matching
    if ':' in category_target:
        cat_name_without_prefix = category_target.split(':', 1)[1]
    else:
        cat_name_without_prefix = category_target

    # Match [[Category:...]] with optional sort key
    pattern = _build_category_pattern(cat_name_without_prefix, 'Category')
    return bool(re.search(pattern, text, re.IGNORECASE))


def is_ar_stub_or_maintenance_category(category_name):
    """
    Check if an Arabic category is a stub or maintenance category.

    Stub categories start with "بذرة" or contain stub-related terms.
    Maintenance categories contain "صيانة" in the name.

    Args:
        category_name: Name of the category (with or without "تصنيف:" prefix)

    Returns:
        bool: True if category is a stub or maintenance category, False otherwise
    """
    # Remove prefix if present
    if ':' in category_name:
        category_name = category_name.split(':', 1)[1]

    # Check if category name starts with "بذرة" (stub)
    if category_name.startswith('بذرة'):
        return True

    # Check for stub-related terms (بذور = stubs)
    # Note: بذرة is already checked with startswith above, so only check بذور here
    if 'بذور' in category_name:
        return True

    # Check for maintenance-related terms (صيانة = maintenance)
    if 'صيانة' in category_name:
        return True

    return False


def is_en_stub_or_maintenance_category(category_name):
    """
    Check if an English category is a stub or maintenance category.

    Stub categories typically contain "stub" in the name.
    Maintenance categories contain "maintenance" in the name.

    Args:
        category_name: Name of the category (with or without "Category:" prefix)

    Returns:
        bool: True if category is a stub or maintenance category, False otherwise
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
