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
import re
import itertools


def load_credentials():
    """
    Load Wikipedia credentials from environment variables.
    
    Returns:
        tuple: (username, password) from environment variables
    
    Raises:
        ValueError: If credentials are not found in environment
    """
    username = os.environ.get('WIKI_USERNAME')
    password = os.environ.get('WIKI_PASSWORD')
    
    if not username or not password:
        raise ValueError(
            "Credentials not found. Please set WIKI_USERNAME and WIKI_PASSWORD environment variables."
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


def get_unused_categories(site, limit=10):
    """
    Fetch unused categories from Wikipedia.
    
    Args:
        site: mwclient.Site object
        limit: Maximum number of categories to fetch
    
    Returns:
        list: List of unused category page objects
    """
    print(f"Fetching up to {limit} unused categories...")
    
    # Use itertools.islice to ensure we only fetch the specified number
    categories = list(itertools.islice(site.querypage('Unusedcategories'), limit))
    
    print(f"Found {len(categories)} unused categories")
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
    pattern = r'\[\[\s*(?:تصنيف|Category)\s*:\s*' + re.escape(category_name) + r'\s*(?:\|[^\]]*?)?\]\]'
    return bool(re.search(pattern, text, re.IGNORECASE))


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
        text = page.text()
        
        # Check if category already exists
        if category_in_text(text, category_name):
            return False
        
        # Add category at the end of the text
        new_text = text.rstrip() + f"\n[[تصنيف:{category_name}]]"
        
        # Save the page
        page.save(new_text, summary=summary)
        return True
        
    except (mwclient.errors.APIError, mwclient.errors.EditError) as e:
        print(f"Error adding category to {page.name}: {e}")
        return False


def process_category(ar_site, en_site, ar_category):
    """
    Process a single unused category from Arabic Wikipedia.
    
    Args:
        ar_site: Arabic Wikipedia site object
        en_site: English Wikipedia site object
        ar_category: Arabic category page object
    """
    category_name = ar_category['title']
    
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
    
    # Get English Wikipedia link
    en_category_title = get_interwiki_link(ar_category_page, 'en')
    
    if not en_category_title:
        print(f"No English Wikipedia link found for {category_name}")
        return
    
    print(f"English Wikipedia category: {en_category_title}")
    
    # Get members of the English category
    en_members = get_category_members(en_site, en_category_title, namespace=0)
    
    if not en_members:
        print(f"No members found in English category {en_category_title}")
        return
    
    print(f"Found {len(en_members)} members in English category")
    
    # Process each member
    added_count = 0
    for en_member in en_members:
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
    """
    print("Starting Unused Categories Bot for Arabic Wikipedia")
    print("="*60)
    
    try:
        # Load credentials
        username, password = load_credentials()
        
        # Connect to Arabic and English Wikipedia
        ar_site = connect_to_wikipedia('ar.wikipedia.org', username, password)
        en_site = connect_to_wikipedia('en.wikipedia.org', username, password)
        
        # Fetch unused categories from Arabic Wikipedia
        # Using a reasonable limit to avoid processing too many categories at once
        unused_categories = get_unused_categories(ar_site, limit=10)
        
        if not unused_categories:
            print("No unused categories found")
            return
        
        # Process each unused category
        for category in unused_categories:
            try:
                process_category(ar_site, en_site, category)
            except Exception as e:
                print(f"Error processing category: {e}")
                continue
        
        print("\n" + "="*60)
        print("Bot execution completed")
        print("="*60)
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
