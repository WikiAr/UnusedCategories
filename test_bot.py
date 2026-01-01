#!/usr/bin/env python3
"""
Unit tests for unused_categories_bot.py

These tests verify the core functionality of the bot without
connecting to Wikipedia.
"""

import unittest
import sys
import os

# Add parent directory to path to import the bot module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


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


class TestAskMode(unittest.TestCase):
    """Test the interactive confirmation mode functionality."""

    def test_set_ask_mode(self):
        """Test that ask mode can be enabled and disabled."""
        from unused_categories_bot import set_ask_mode, is_ask_mode

        # Initially should be False (default)
        set_ask_mode(False)
        self.assertFalse(is_ask_mode())

        # Enable ask mode
        set_ask_mode(True)
        self.assertTrue(is_ask_mode())

        # Disable ask mode
        set_ask_mode(False)
        self.assertFalse(is_ask_mode())

    def test_confirm_edit_without_ask_mode(self):
        """Test that confirm_edit returns True when ask mode is disabled."""
        from unused_categories_bot import confirm_edit, set_ask_mode

        set_ask_mode(False)
        result = confirm_edit("Test Page", "old text", "new text")
        self.assertTrue(result)

    def test_confirm_edit_with_yes_response(self):
        """Test that confirm_edit returns True when user enters 'y'."""
        from unused_categories_bot import confirm_edit, set_ask_mode
        from unittest.mock import patch
        import unused_categories_bot

        # Reset auto_approve_all state
        unused_categories_bot._auto_approve_all = False
        set_ask_mode(True)

        with patch('builtins.input', return_value='y'):
            result = confirm_edit("Test Page", "old text", "new text")
            self.assertTrue(result)

        set_ask_mode(False)

    def test_confirm_edit_with_empty_response(self):
        """Test that confirm_edit returns True when user enters empty string."""
        from unused_categories_bot import confirm_edit, set_ask_mode
        from unittest.mock import patch
        import unused_categories_bot

        # Reset auto_approve_all state
        unused_categories_bot._auto_approve_all = False
        set_ask_mode(True)

        with patch('builtins.input', return_value=''):
            result = confirm_edit("Test Page", "old text", "new text")
            self.assertTrue(result)

        set_ask_mode(False)

    def test_confirm_edit_with_no_response(self):
        """Test that confirm_edit returns False when user enters 'n'."""
        from unused_categories_bot import confirm_edit, set_ask_mode
        from unittest.mock import patch
        import unused_categories_bot

        # Reset auto_approve_all state
        unused_categories_bot._auto_approve_all = False
        set_ask_mode(True)

        with patch('builtins.input', return_value='n'):
            result = confirm_edit("Test Page", "old text", "new text")
            self.assertFalse(result)

        set_ask_mode(False)

    def test_confirm_edit_with_all_response(self):
        """Test that confirm_edit sets auto_approve_all when user enters 'a'."""
        from unused_categories_bot import confirm_edit, set_ask_mode
        from unittest.mock import patch
        import unused_categories_bot

        # Reset auto_approve_all state
        unused_categories_bot._auto_approve_all = False
        set_ask_mode(True)

        with patch('builtins.input', return_value='a'):
            result = confirm_edit("Test Page", "old text", "new text")
            self.assertTrue(result)
            self.assertTrue(unused_categories_bot._auto_approve_all)

        # Reset for other tests
        unused_categories_bot._auto_approve_all = False
        set_ask_mode(False)

    def test_confirm_edit_auto_approve_skips_prompt(self):
        """Test that confirm_edit skips prompt when auto_approve_all is True."""
        from unused_categories_bot import confirm_edit, set_ask_mode
        from unittest.mock import patch
        import unused_categories_bot

        # Set auto_approve_all to True
        unused_categories_bot._auto_approve_all = True
        set_ask_mode(True)

        # input should not be called when auto_approve_all is True
        with patch('builtins.input') as mock_input:
            result = confirm_edit("Test Page", "old text", "new text")
            self.assertTrue(result)
            mock_input.assert_not_called()

        # Reset for other tests
        unused_categories_bot._auto_approve_all = False
        set_ask_mode(False)


if __name__ == '__main__':
    unittest.main()
