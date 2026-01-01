import sys
import os
import pytest
import unittest
# Add parent directory to path to import utils module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import (
    category_in_text,
    en_page_has_category_in_text,
    is_ar_stub_or_maintenance_category,
    is_en_stub_or_maintenance_category
)


class TestCategoryFiltering(unittest.TestCase):
    """Test the category filtering functionality."""

    def test_ar_stub_category_starts_with_budhra(self):
        """Test that Arabic category starting with بذرة is detected as stub."""

        self.assertTrue(is_ar_stub_or_maintenance_category("بذرة علم"))
        self.assertTrue(is_ar_stub_or_maintenance_category("تصنيف:بذرة علم"))

    def test_ar_stub_category_contains_budhur(self):
        """Test that Arabic category containing بذور is detected as stub."""

        self.assertTrue(is_ar_stub_or_maintenance_category("مقالات بذور"))
        self.assertTrue(is_ar_stub_or_maintenance_category("تصنيف:بذور علم"))

    def test_ar_maintenance_category(self):
        """Test that Arabic maintenance category is detected."""

        self.assertTrue(is_ar_stub_or_maintenance_category("صيانة ويكيبيديا"))
        self.assertTrue(is_ar_stub_or_maintenance_category("تصنيف:صيانة"))

    def test_ar_normal_category(self):
        """Test that normal Arabic category is not flagged."""

        self.assertFalse(is_ar_stub_or_maintenance_category("تاريخ"))
        self.assertFalse(is_ar_stub_or_maintenance_category("تصنيف:علوم"))

    def test_en_stub_category(self):
        """Test that English stub category is detected."""

        self.assertTrue(is_en_stub_or_maintenance_category("Science stubs"))
        self.assertTrue(is_en_stub_or_maintenance_category("Category:Stub articles"))

    def test_en_maintenance_category(self):
        """Test that English maintenance category is detected."""

        self.assertTrue(is_en_stub_or_maintenance_category("Wikipedia maintenance"))
        self.assertTrue(is_en_stub_or_maintenance_category("Category:Maintenance templates"))

    def test_en_normal_category(self):
        """Test that normal English category is not flagged."""

        self.assertFalse(is_en_stub_or_maintenance_category("History"))
        self.assertFalse(is_en_stub_or_maintenance_category("Category:Science"))


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
        text = """Some article text\n[[تصنيف:تاريخ]]\n[[تصنيف:علوم]]\n[[تصنيف:جغرافيا]]\n"""
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
        text = """Article beginning\n[[تصنيف:تاريخ]]\nMore article text here\n"""
        self.assertTrue(category_in_text(text, "تاريخ"))


class TestCategoryFilteringMock:
    """Test the category filtering functionality."""

    def test_en_page_has_category_in_text_found(self):
        text = "Article text\n[[Category:History]]\nMore text"

        assert en_page_has_category_in_text(text, "History") is True
        assert en_page_has_category_in_text(text, "Category:History") is True

    def test_en_page_has_category_in_text_not_found(self):
        text = "Article text\n[[Category:Science]]\nMore text"

        assert en_page_has_category_in_text(text, "History") is False

    def test_en_page_has_category_with_sort_key(self):
        text = "Article text\n[[Category:History|Key]]\nMore text"

        assert en_page_has_category_in_text(text, "History") is True

    def test_en_page_has_category_case_insensitive(self):
        text = "Article text\n[[category:history]]\nMore text"

        assert en_page_has_category_in_text(text, "History") is True
