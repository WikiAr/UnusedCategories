import sys
import os
import pytest
# Add parent directory to path to import utils module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import (
    category_in_text,
    en_page_has_category_in_text,
    is_ar_stub_or_maintenance_category,
    is_en_stub_or_maintenance_category
)


class TestCategoryFiltering:
    """Test the category filtering functionality."""

    def test_ar_stub_category_starts_with_budhra(self):
        """Arabic category starting with بذرة should be detected as stub."""
        assert is_ar_stub_or_maintenance_category("بذرة علم") is True
        assert is_ar_stub_or_maintenance_category("تصنيف:بذرة علم") is True

    def test_ar_stub_category_contains_budhur(self):
        """Arabic category containing بذور should be detected as stub."""
        assert is_ar_stub_or_maintenance_category("مقالات بذور") is True
        assert is_ar_stub_or_maintenance_category("تصنيف:بذور علم") is True

    def test_ar_maintenance_category(self):
        """Arabic maintenance category should be detected."""
        assert is_ar_stub_or_maintenance_category("صيانة ويكيبيديا") is True
        assert is_ar_stub_or_maintenance_category("تصنيف:صيانة") is True

    def test_ar_normal_category(self):
        """Normal Arabic category should not be flagged."""
        assert is_ar_stub_or_maintenance_category("تاريخ") is False
        assert is_ar_stub_or_maintenance_category("تصنيف:علوم") is False

    def test_en_stub_category(self):
        """English stub category should be detected."""
        assert is_en_stub_or_maintenance_category("Science stubs") is True
        assert is_en_stub_or_maintenance_category("Category:Stub articles") is True

    def test_en_maintenance_category(self):
        """English maintenance category should be detected."""
        assert is_en_stub_or_maintenance_category("Wikipedia maintenance") is True
        assert is_en_stub_or_maintenance_category("Category:Maintenance templates") is True

    def test_en_normal_category(self):
        """Normal English category should not be flagged."""
        assert is_en_stub_or_maintenance_category("History") is False
        assert is_en_stub_or_maintenance_category("Category:Science") is False


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
