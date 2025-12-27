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


if __name__ == '__main__':
    unittest.main()
