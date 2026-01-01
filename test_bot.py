#!/usr/bin/env python3
"""
Unit tests for unused_categories_bot.py

These tests verify the core functionality of the bot without
connecting to Wikipedia.
"""

import unittest
import sys
import os

class TestGetUnusedCategories(unittest.TestCase):
    """Test the unused categories fetching functionality."""

    def test_get_unused_categories_returns_results(self):
        """Test that get_unused_categories parses API response correctly."""
        from unused_categories_bot import get_unused_categories
        from unittest.mock import Mock

        # Create mock site object
        mock_site = Mock()
        mock_site.get.return_value = {
            'query': {
                'querypage': {
                    'name': 'Unusedcategories',
                    'results': [
                        {'title': 'تصنيف:تاريخ', 'ns': 14},
                        {'title': 'تصنيف:علوم', 'ns': 14},
                    ]
                }
            }
        }

        categories = get_unused_categories(mock_site, limit=10)

        # Verify the API was called correctly
        mock_site.get.assert_called_once_with(
            'query', list='querypage', qppage='Unusedcategories', qplimit=10
        )

        # Verify results are returned
        self.assertEqual(len(categories), 2)
        self.assertEqual(categories[0]['title'], 'تصنيف:تاريخ')
        self.assertEqual(categories[1]['title'], 'تصنيف:علوم')

    def test_get_unused_categories_empty_results(self):
        """Test that get_unused_categories handles empty results."""
        from unused_categories_bot import get_unused_categories
        from unittest.mock import Mock

        # Create mock site object with empty results
        mock_site = Mock()
        mock_site.get.return_value = {
            'query': {
                'querypage': {
                    'name': 'Unusedcategories',
                    'results': []
                }
            }
        }

        categories = get_unused_categories(mock_site, limit=10)

        self.assertEqual(len(categories), 0)

    def test_get_unused_categories_missing_query(self):
        """Test that get_unused_categories handles missing query key."""
        from unused_categories_bot import get_unused_categories
        from unittest.mock import Mock

        # Create mock site object with malformed response
        mock_site = Mock()
        mock_site.get.return_value = {}

        categories = get_unused_categories(mock_site, limit=10)

        self.assertEqual(len(categories), 0)


class TestCredentialLoading(unittest.TestCase):
    """Test credential loading functionality."""

    def test_credentials_missing(self):
        """Test that missing credentials raise ValueError."""
        from unused_categories_bot import load_credentials

        # Save current env vars
        old_username = os.environ.get('WIKI_USERNAME')
        old_password = os.environ.get('WIKI_PASSWORD')

        try:
            # Remove env vars
            if 'WIKI_USERNAME' in os.environ:
                del os.environ['WIKI_USERNAME']
            if 'WIKI_PASSWORD' in os.environ:
                del os.environ['WIKI_PASSWORD']

            # Should raise ValueError
            with self.assertRaises(ValueError):
                load_credentials()
        finally:
            # Restore env vars
            if old_username:
                os.environ['WIKI_USERNAME'] = old_username
            if old_password:
                os.environ['WIKI_PASSWORD'] = old_password

    def test_credentials_present(self):
        """Test that credentials are loaded correctly."""
        from unused_categories_bot import load_credentials

        # Save current env vars
        old_username = os.environ.get('WIKI_USERNAME')
        old_password = os.environ.get('WIKI_PASSWORD')

        try:
            # Set test env vars
            os.environ['WIKI_USERNAME'] = 'test_user'
            os.environ['WIKI_PASSWORD'] = 'test_pass'

            username, password = load_credentials()
            self.assertEqual(username, 'test_user')
            self.assertEqual(password, 'test_pass')
        finally:
            # Restore env vars
            if old_username:
                os.environ['WIKI_USERNAME'] = old_username
            else:
                if 'WIKI_USERNAME' in os.environ:
                    del os.environ['WIKI_USERNAME']

            if old_password:
                os.environ['WIKI_PASSWORD'] = old_password
            else:
                if 'WIKI_PASSWORD' in os.environ:
                    del os.environ['WIKI_PASSWORD']


class TestHiddenCategoryCheck(unittest.TestCase):
    """Test the hidden category check functionality."""

    def test_hidden_category_detected(self):
        """Test that hidden category is detected."""
        from unused_categories_bot import is_hidden_category
        from unittest.mock import Mock

        mock_page = Mock()
        mock_site = Mock()
        mock_page.site = mock_site
        mock_page.name = "Category:Hidden test"

        mock_site.get.return_value = {
            'query': {
                'pages': {
                    '123': {
                        'categoryinfo': {
                            'hidden': True
                        }
                    }
                }
            }
        }

        self.assertTrue(is_hidden_category(mock_page))

    def test_visible_category_not_flagged(self):
        """Test that visible category is not flagged as hidden."""
        from unused_categories_bot import is_hidden_category
        from unittest.mock import Mock

        mock_page = Mock()
        mock_site = Mock()
        mock_page.site = mock_site
        mock_page.name = "Category:Visible test"

        mock_site.get.return_value = {
            'query': {
                'pages': {
                    '123': {
                        'categoryinfo': {
                            'hidden': False
                        }
                    }
                }
            }
        }

        self.assertFalse(is_hidden_category(mock_page))

    def test_category_without_categoryinfo(self):
        """Test that category without categoryinfo is not flagged."""
        from unused_categories_bot import is_hidden_category
        from unittest.mock import Mock

        mock_page = Mock()
        mock_site = Mock()
        mock_page.site = mock_site
        mock_page.name = "Category:Test"

        mock_site.get.return_value = {
            'query': {
                'pages': {
                    '123': {}
                }
            }
        }

        self.assertFalse(is_hidden_category(mock_page))


class TestRedirectPageCheck(unittest.TestCase):
    """Test the redirect page check functionality."""

    def test_redirect_page_detected(self):
        """Test that redirect page is detected."""
        from unused_categories_bot import is_redirect_page
        from unittest.mock import Mock

        mock_page = Mock()
        # redirects_to() returns the target page for redirects
        mock_page.redirects_to.return_value = Mock()  # Non-None means it's a redirect

        self.assertTrue(is_redirect_page(mock_page))

    def test_non_redirect_page_not_flagged(self):
        """Test that non-redirect page is not flagged."""
        from unused_categories_bot import is_redirect_page
        from unittest.mock import Mock

        mock_page = Mock()
        # redirects_to() returns None for non-redirects
        mock_page.redirects_to.return_value = None

        self.assertFalse(is_redirect_page(mock_page))

    def test_redirect_check_handles_api_error(self):
        """Test that redirect check handles API errors gracefully."""
        from unused_categories_bot import is_redirect_page
        from unittest.mock import Mock
        import mwclient.errors

        mock_page = Mock()
        mock_page.name = "Test Page"
        mock_page.redirects_to.side_effect = mwclient.errors.APIError('error', 'info', {})

        # Should return False on error
        self.assertFalse(is_redirect_page(mock_page))

    def test_add_category_skips_redirect_page(self):
        """Test that add_category_to_page skips redirect pages."""
        from unused_categories_bot import add_category_to_page
        from unittest.mock import Mock

        mock_page = Mock()
        # redirects_to() returns the target page for redirects
        mock_page.redirects_to.return_value = Mock()  # Non-None means it's a redirect
        mock_page.name = "Test Redirect Page"

        # Should return False for redirect pages without calling text() or save()
        result = add_category_to_page(mock_page, "TestCategory", "Test summary")
        self.assertFalse(result)
        mock_page.text.assert_not_called()
        mock_page.save.assert_not_called()
