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


class TestCategoryDetection:
    """Test the category detection functionality."""

    def test_category_found_arabic(self):
        """Arabic category syntax should be detected."""
        text = "Some article text\n[[تصنيف:تاريخ]]\n"
        assert category_in_text(text, "تاريخ") is True

    def test_category_found_with_spaces(self):
        """Category with surrounding spaces should be detected."""
        text = "Some article text\n[[تصنيف: علم الفلك ]]\n"
        assert category_in_text(text, "علم الفلك") is True

    def test_category_not_found(self):
        """Missing category should not be detected."""
        text = "Some article text\n[[تصنيف:تاريخ]]\n"
        assert category_in_text(text, "علوم") is False

    def test_category_found_english_syntax(self):
        """English category syntax should be detected."""
        text = "Some article text\n[[Category:History]]\n"
        assert category_in_text(text, "History") is True

    def test_category_with_sort_key(self):
        """Category with sort key should be detected."""
        text = "Some article text\n[[تصنيف:تاريخ|مفتاح]]\n"
        assert category_in_text(text, "تاريخ") is True

    def test_category_case_insensitive(self):
        """Category detection should be case insensitive."""
        text = "Some article text\n[[category:History]]\n"
        assert category_in_text(text, "History") is True

    def test_multiple_categories(self):
        """Multiple categories should all be detected correctly."""
        text = (
            "Some article text\n"
            "[[تصنيف:تاريخ]]\n"
            "[[تصنيف:علوم]]\n"
            "[[تصنيف:جغرافيا]]\n"
        )

        assert category_in_text(text, "علوم") is True
        assert category_in_text(text, "تاريخ") is True
        assert category_in_text(text, "جغرافيا") is True
        assert category_in_text(text, "رياضيات") is False

    def test_empty_text(self):
        """Empty text should not match any category."""
        assert category_in_text("", "تاريخ") is False

    def test_category_in_middle_of_text(self):
        """Category should be detected even if not at the end."""
        text = (
            "Article beginning\n"
            "[[تصنيف:تاريخ]]\n"
            "More article text here\n"
        )

        assert category_in_text(text, "تاريخ") is True


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
