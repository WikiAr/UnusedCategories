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

from unused_categories_bot import category_in_text


class TestCategoryDetection(unittest.TestCase):
    """Test the category detection functionality."""
    
    def test_category_found_arabic(self):
        """Test that Arabic category syntax is detected."""
        text = "Some article text\n[[تصنيف:تاريخ]]\n"
        self.assertTrue(category_in_text(text, "تاريخ"))
    
    def test_category_found_with_spaces(self):
        """Test that category with spaces is detected."""
        text = "Some article text\n[[تصنيف: علم الفلك ]]\n"
        self.assertTrue(category_in_text(text, "علم الفلك"))
    
    def test_category_not_found(self):
        """Test that missing category is not detected."""
        text = "Some article text\n[[تصنيف:تاريخ]]\n"
        self.assertFalse(category_in_text(text, "علوم"))
    
    def test_category_found_english_syntax(self):
        """Test that English category syntax is detected."""
        text = "Some article text\n[[Category:History]]\n"
        self.assertTrue(category_in_text(text, "History"))
    
    def test_category_with_sort_key(self):
        """Test that category with sort key is detected."""
        text = "Some article text\n[[تصنيف:تاريخ|مفتاح]]\n"
        self.assertTrue(category_in_text(text, "تاريخ"))
    
    def test_category_case_insensitive(self):
        """Test that category detection is case insensitive."""
        text = "Some article text\n[[category:History]]\n"
        self.assertTrue(category_in_text(text, "History"))
    
    def test_multiple_categories(self):
        """Test detection with multiple categories present."""
        text = """Some article text
[[تصنيف:تاريخ]]
[[تصنيف:علوم]]
[[تصنيف:جغرافيا]]
"""
        self.assertTrue(category_in_text(text, "علوم"))
        self.assertTrue(category_in_text(text, "تاريخ"))
        self.assertTrue(category_in_text(text, "جغرافيا"))
        self.assertFalse(category_in_text(text, "رياضيات"))
    
    def test_empty_text(self):
        """Test with empty article text."""
        text = ""
        self.assertFalse(category_in_text(text, "تاريخ"))
    
    def test_category_in_middle_of_text(self):
        """Test category detection when not at the end."""
        text = """Article beginning
[[تصنيف:تاريخ]]
More article text here
"""
        self.assertTrue(category_in_text(text, "تاريخ"))


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


class TestCategoryFiltering(unittest.TestCase):
    """Test the category filtering functionality."""
    
    def test_ar_stub_category_starts_with_budhra(self):
        """Test that Arabic category starting with بذرة is detected as stub."""
        from unused_categories_bot import is_ar_stub_or_maintenance_category
        
        self.assertTrue(is_ar_stub_or_maintenance_category("بذرة علم"))
        self.assertTrue(is_ar_stub_or_maintenance_category("تصنيف:بذرة علم"))
    
    def test_ar_stub_category_contains_budhur(self):
        """Test that Arabic category containing بذور is detected as stub."""
        from unused_categories_bot import is_ar_stub_or_maintenance_category
        
        self.assertTrue(is_ar_stub_or_maintenance_category("مقالات بذور"))
        self.assertTrue(is_ar_stub_or_maintenance_category("تصنيف:بذور علم"))
    
    def test_ar_maintenance_category(self):
        """Test that Arabic maintenance category is detected."""
        from unused_categories_bot import is_ar_stub_or_maintenance_category
        
        self.assertTrue(is_ar_stub_or_maintenance_category("صيانة ويكيبيديا"))
        self.assertTrue(is_ar_stub_or_maintenance_category("تصنيف:صيانة"))
    
    def test_ar_normal_category(self):
        """Test that normal Arabic category is not flagged."""
        from unused_categories_bot import is_ar_stub_or_maintenance_category
        
        self.assertFalse(is_ar_stub_or_maintenance_category("تاريخ"))
        self.assertFalse(is_ar_stub_or_maintenance_category("تصنيف:علوم"))
    
    def test_en_stub_category(self):
        """Test that English stub category is detected."""
        from unused_categories_bot import is_en_stub_or_maintenance_category
        
        self.assertTrue(is_en_stub_or_maintenance_category("Science stubs"))
        self.assertTrue(is_en_stub_or_maintenance_category("Category:Stub articles"))
    
    def test_en_maintenance_category(self):
        """Test that English maintenance category is detected."""
        from unused_categories_bot import is_en_stub_or_maintenance_category
        
        self.assertTrue(is_en_stub_or_maintenance_category("Wikipedia maintenance"))
        self.assertTrue(is_en_stub_or_maintenance_category("Category:Maintenance templates"))
    
    def test_en_normal_category(self):
        """Test that normal English category is not flagged."""
        from unused_categories_bot import is_en_stub_or_maintenance_category
        
        self.assertFalse(is_en_stub_or_maintenance_category("History"))
        self.assertFalse(is_en_stub_or_maintenance_category("Category:Science"))
    
    def test_en_page_has_category_in_text_found(self):
        """Test that category in page text is detected."""
        from unused_categories_bot import en_page_has_category_in_text
        from unittest.mock import Mock
        
        mock_page = Mock()
        mock_page.text.return_value = "Article text\n[[Category:History]]\nMore text"
        
        self.assertTrue(en_page_has_category_in_text(mock_page, "History"))
        self.assertTrue(en_page_has_category_in_text(mock_page, "Category:History"))
    
    def test_en_page_has_category_in_text_not_found(self):
        """Test that missing category is not detected."""
        from unused_categories_bot import en_page_has_category_in_text
        from unittest.mock import Mock
        
        mock_page = Mock()
        mock_page.text.return_value = "Article text\n[[Category:Science]]\nMore text"
        
        self.assertFalse(en_page_has_category_in_text(mock_page, "History"))
    
    def test_en_page_has_category_with_sort_key(self):
        """Test that category with sort key is detected."""
        from unused_categories_bot import en_page_has_category_in_text
        from unittest.mock import Mock
        
        mock_page = Mock()
        mock_page.text.return_value = "Article text\n[[Category:History|Key]]\nMore text"
        
        self.assertTrue(en_page_has_category_in_text(mock_page, "History"))
    
    def test_en_page_has_category_case_insensitive(self):
        """Test that category detection is case insensitive."""
        from unused_categories_bot import en_page_has_category_in_text
        from unittest.mock import Mock
        
        mock_page = Mock()
        mock_page.text.return_value = "Article text\n[[category:history]]\nMore text"
        
        self.assertTrue(en_page_has_category_in_text(mock_page, "History"))


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
