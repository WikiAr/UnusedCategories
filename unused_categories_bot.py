#!/usr/bin/env python3
"""
Unused Categories Bot for Arabic Wikipedia

This script processes unused categories on Arabic Wikipedia by:
1. Fetching unused categories from Arabic Wikipedia
2. Finding corresponding categories on English Wikipedia
3. Getting members of English categories
4. Finding Arabic equivalents of those articles
5. Adding the Arabic category to articles that don't have it
"""

import os
import sys
import mwclient
import difflib
from dotenv import load_dotenv

from utils import (
    en_page_has_category_in_text,
    category_in_text,
    is_ar_stub_or_maintenance_category,
    is_en_stub_or_maintenance_category,
)

load_dotenv()

# Global state for interactive confirmation mode
_ask_mode = False
_auto_approve_all = False


def set_ask_mode(enabled):
    """
    Enable or disable interactive confirmation mode.

    Args:
        enabled: True to enable ask mode, False to disable
    """
    global _ask_mode
    _ask_mode = enabled


def is_ask_mode():
    """
    Check if interactive confirmation mode is enabled.

    Returns:
        bool: True if ask mode is enabled
    """
    return _ask_mode


def confirm_edit(page_title, old_text, new_text):
    """
    Ask user to confirm an edit in interactive mode.

    Shows the target page, text diff, and prompts for confirmation.

    Args:
        page_title: Title of the page being edited
        old_text: Original page text
        new_text: New page text after edit

    Returns:
        bool: True if edit should proceed, False to skip
    """
    global _auto_approve_all

    # If auto-approve is enabled, skip confirmation
    if _auto_approve_all:
        return True

    # If not in ask mode, proceed without confirmation
    if not _ask_mode:
        return True

    # Show target page
    print(f"\n{'='*60}")
    print(f"Target: {page_title}")
    print(f"{'='*60}")

    # Show diff
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff = difflib.unified_diff(old_lines, new_lines, fromfile='before', tofile='after', lineterm='')
    diff_text = ''.join(diff)

    if diff_text:
        print("Diff:")
        print(diff_text)
    else:
        print("No changes detected.")

    print(f"{'='*60}")

    # Prompt for confirmation
    print("Options: [y]es / [n]o / [a]ll (approve all remaining)")
    response = input("Confirm edit? [Y/n/a]: ").strip().lower()

    # Empty response or "y"/"yes" means proceed with this edit
    if response in ('', 'y', 'yes'):
        return True

    # "a" means approve all remaining edits
    if response == 'a':
        _auto_approve_all = True
        print("Auto-approving all remaining edits.")
        return True

    # Any other response means skip
    print("Edit skipped.")
    return False


def is_hidden_category(category_page):
    """
    Check if a category is a hidden category.

    Hidden categories are categories that have the __HIDDENCAT__ magic word
    or are in a hidden category parent.

    Args:
        category_page: mwclient.Page object of the category

    Returns:
        bool: True if category is hidden, False otherwise
    """
    try:
        # Get category info including hidden property
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
    except (mwclient.errors.APIError, KeyError) as e:
        print(f"Error checking hidden category for {category_page.name}: {e}")

    return False


def should_skip_ar_category(category_page):
    """
    Check if an Arabic category should be skipped.

    Categories to skip:
    - Hidden categories
    - Maintenance categories
    - Stub categories
    - Categories starting with "بذرة"

    Args:
        category_page: mwclient.Page object of the Arabic category

    Returns:
        bool: True if category should be skipped, False otherwise
    """
    # Check if hidden
    if is_hidden_category(category_page):
        print(f"  Skipping hidden category: {category_page.name}")
        return True

    # Check if stub or maintenance category
    if is_ar_stub_or_maintenance_category(category_page.name):
        print(f"  Skipping stub/maintenance category: {category_page.name}")
        return True

    return False


def should_skip_en_category(category_page):
    """
    Check if an English category should be skipped.

    Categories to skip:
    - Hidden categories
    - Maintenance categories
    - Stub categories

    Args:
        category_page: mwclient.Page object of the English category

    Returns:
        bool: True if category should be skipped, False otherwise
    """
    # Check if hidden
    if is_hidden_category(category_page):
        print(f"  Skipping hidden English category: {category_page.name}")
        return True

    # Check if stub or maintenance category
    if is_en_stub_or_maintenance_category(category_page.name):
        print(f"  Skipping stub/maintenance English category: {category_page.name}")
        return True

    return False


def is_redirect_page(page):
    """
    Check if a page is a redirect.

    Uses mwclient's redirects_to() method which returns None if the page
    is not a redirect, or the target page if it is a redirect.

    Args:
        page: mwclient.Page object

    Returns:
        bool: True if page is a redirect, False otherwise
    """
    try:
        return page.redirects_to() is not None
    except mwclient.errors.APIError as e:
        print(f"API error checking redirect status for {page.name}: {e}")
        return False
    except AttributeError as e:
        print(f"Attribute error checking redirect status for {page.name}: {e}")
        return False


def load_credentials():
    """
    Load Wikipedia credentials from environment variables.

    Returns:
        tuple: (username, password) from environment variables

    Raises:
        ValueError: If credentials are not found in environment
    """
    username = os.environ.get('WM_USERNAME')
    password = os.environ.get('PASSWORD')

    if not username or not password:
        raise ValueError(
            "Credentials not found. Please set WM_USERNAME and PASSWORD environment variables."
        )

    return username, password


def connect_to_wikipedia(site_url, username, password):
    """
    Connect to Wikipedia using mwclient.

    Args:
        site_url: Wikipedia site URL (e.g., 'ar.wikipedia.org')
        username: Wikipedia username
        password: Wikipedia password

    Returns:
        mwclient.Site: Connected site object
    """
    site = mwclient.Site(site_url, scheme='https')
    site.login(username, password)
    print(f"Successfully connected to {site_url}")
    return site


def get_unused_categories(site, limit=1000):
    """
    Fetch unused categories from Wikipedia.

    Args:
        site: mwclient.Site object
        limit: Maximum number of categories to fetch

    Returns:
        list: List of unused category titles
    """
    print(f"Fetching up to {limit} unused categories...")

    categories = []
    try:
        # Use the MediaWiki API's querypage list to get unused categories
        # API: action=query&list=querypage&qppage=Unusedcategories&qplimit=N
        result = site.get('query', list='querypage', qppage='Unusedcategories', qplimit=limit)

        if 'query' in result and 'querypage' in result['query']:
            querypage_data = result['query']['querypage']
            if 'results' in querypage_data:
                categories = querypage_data['results']
    except mwclient.errors.APIError as e:
        print(f"API error fetching unused categories: {e}")

    print(f"Found {len(categories)} unused categories")
    categories = [cat['title'] for cat in categories]
    return categories


def get_interwiki_link(page, target_lang):
    """
    Get interwiki link from a page to a target language.

    Args:
        page: mwclient.Page object
        target_lang: Target language code (e.g., 'en')

    Returns:
        str or None: Title of the page in target language, or None if not found
    """
    try:
        langlinks = page.langlinks()
        for lang, title in langlinks:
            if lang == target_lang:
                return title
    except (mwclient.errors.APIError, AttributeError) as e:
        print(f"Error getting interwiki link for {page.name}: {e}")

    return None


def get_category_members(site, category_title, namespace=0):
    """
    Get members of a category.

    Args:
        site: mwclient.Site object
        category_title: Title of the category
        namespace: Namespace to filter members (0 for articles)

    Returns:
        list: List of page objects that are members of the category
    """
    try:
        category = site.pages[category_title]
        # Use list comprehension for efficiency
        return list(category.members(namespace=namespace))
    except (mwclient.errors.APIError, KeyError) as e:
        print(f"Error getting category members for {category_title}: {e}")
        return []


def add_category_to_page(page, category_name, summary):
    """
    Add a category to a page if it's not already there.

    Args:
        page: mwclient.Page object
        category_name: Name of the category (without "Category:" prefix)
        summary: Edit summary

    Returns:
        bool: True if category was added, False otherwise
    """
    try:
        # Skip redirect pages
        if is_redirect_page(page):
            return False

        text = page.text()

        # Check if category already exists
        if category_in_text(text, category_name):
            return False

        # Add category at the end of the text
        new_text = text.rstrip() + f"\n[[تصنيف:{category_name}]]"

        # Ask for confirmation if in ask mode
        if not confirm_edit(page.name, text, new_text):
            return False

        # Save the page
        page.save(new_text, summary=summary)
        return True

    except (mwclient.errors.APIError, mwclient.errors.EditError) as e:
        print(f"Error adding category to {page.name}: {e}")
        return False


def process_category(ar_site, en_site, category_name):
    """
    Process a single unused category from Arabic Wikipedia.

    Args:
        ar_site: Arabic Wikipedia site object
        en_site: English Wikipedia site object
        category_name: Name of the category (without "تصنيف:" prefix)
    """
    # Remove "تصنيف:" prefix
    if ':' in category_name:
        category_name_without_prefix = category_name.split(':', 1)[1]
    else:
        category_name_without_prefix = category_name

    print(f"\n{'='*60}")
    print(f"Processing: {category_name}")
    print(f"{'='*60}")

    # Get the page object
    ar_category_page = ar_site.pages[category_name]

    # Check if Arabic category should be skipped (hidden, maintenance, stub)
    if should_skip_ar_category(ar_category_page):
        return

    # Get English Wikipedia link
    en_category_title = get_interwiki_link(ar_category_page, 'en')

    if not en_category_title:
        print(f"No English Wikipedia link found for {category_name}")
        return

    print(f"English Wikipedia category: {en_category_title}")

    # Get the English category page object to check if it should be skipped
    en_category_page = en_site.pages[en_category_title]

    # Check if English category should be skipped (hidden, maintenance, stub)
    if should_skip_en_category(en_category_page):
        return

    # Get members of the English category
    en_members = get_category_members(en_site, en_category_title, namespace="0,14")

    if not en_members:
        print(f"No members found in English category {en_category_title}")
        return

    print(f"Found {len(en_members)} members in English category")

    # Process each member
    added_count = 0
    for en_member in en_members:
        # Check if the English page contains the category directly in its text
        # (not added via a template)
        text = en_member.text()
        if not en_page_has_category_in_text(text, en_category_title):
            print(f"  Skipping {en_member.name}: category not in text (possibly added via template)")
            continue

        # Get Arabic Wikipedia link
        ar_article_title = get_interwiki_link(en_member, 'ar')

        if not ar_article_title:
            continue

        print(f"  Checking Arabic article: {ar_article_title}")

        # Get Arabic article page
        ar_article = ar_site.pages[ar_article_title]

        # Add category if not present
        if add_category_to_page(ar_article, category_name_without_prefix, "بوت: أضاف 1 تصنيف"):
            print(f"    ✓ Added category to {ar_article_title}")
            added_count += 1
        else:
            print(f"    - Category already exists in {ar_article_title}")

    print(f"\nTotal categories added: {added_count}")


def main():
    """
    Main function to run the bot.

    Command line arguments:
        ask: Enable interactive confirmation mode for each edit
    """
    # Check for "ask" argument to enable interactive confirmation mode
    if 'ask' in sys.argv:
        set_ask_mode(True)
        print("Interactive confirmation mode enabled.")

    print("Starting Unused Categories Bot for Arabic Wikipedia")
    print("="*60)

    # Load credentials
    username, password = load_credentials()

    # Connect to Arabic and English Wikipedia
    ar_site = connect_to_wikipedia('ar.wikipedia.org', username, password)
    en_site = connect_to_wikipedia('en.wikipedia.org', username, password)

    unused_categories = []
    # use can work in one category by input sys.argv like: -cat:تصنيف:أفلام_مغامرات_سويسرية
    for arg in sys.argv:
        arg, _, value = arg.partition(":")
        if arg == "-cat":
            unused_categories.append(value)

    if not unused_categories:
        # Fetch unused categories from Arabic Wikipedia
        # Using a reasonable limit to avoid processing too many categories at once
        unused_categories = get_unused_categories(ar_site, limit=1000)

    if not unused_categories:
        print("No unused categories found")
        return

    # Process each unused category
    for category in unused_categories:
        process_category(ar_site, en_site, category)

    print("\n" + "="*60)
    print("Bot execution completed")
    print("="*60)


if __name__ == "__main__":
    main()
