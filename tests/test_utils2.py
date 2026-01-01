
import pytest

from utils import (
    category_in_text,
    is_ar_stub_or_maintenance_category,
    is_en_stub_or_maintenance_category
)


@pytest.mark.fast
class TestCategoryFiltering:
    """Test the category filtering functionality."""

    def test_ar_stub_category_starts_with_budhra(self) -> None:
        """Arabic category starting with بذرة should be detected as stub."""
        assert is_ar_stub_or_maintenance_category("بذرة علم") is True
        assert is_ar_stub_or_maintenance_category("تصنيف:بذرة علم") is True

    def test_ar_stub_category_contains_budhur(self) -> None:
        """Arabic category containing بذور should be detected as stub."""
        assert is_ar_stub_or_maintenance_category("مقالات بذور") is True
        assert is_ar_stub_or_maintenance_category("تصنيف:بذور علم") is True

    def test_ar_maintenance_category(self) -> None:
        """Arabic maintenance category should be detected."""
        assert is_ar_stub_or_maintenance_category("صيانة ويكيبيديا") is True
        assert is_ar_stub_or_maintenance_category("تصنيف:صيانة") is True

    def test_ar_normal_category(self) -> None:
        """Normal Arabic category should not be flagged."""
        assert is_ar_stub_or_maintenance_category("تاريخ") is False
        assert is_ar_stub_or_maintenance_category("تصنيف:علوم") is False

    def test_en_stub_category(self) -> None:
        """English stub category should be detected."""
        assert is_en_stub_or_maintenance_category("Science stubs") is True
        assert is_en_stub_or_maintenance_category("Category:Stub articles") is True

    def test_en_maintenance_category(self) -> None:
        """English maintenance category should be detected."""
        assert is_en_stub_or_maintenance_category("Wikipedia maintenance") is True
        assert is_en_stub_or_maintenance_category("Category:Maintenance templates") is True

    def test_en_normal_category(self) -> None:
        """Normal English category should not be flagged."""
        assert is_en_stub_or_maintenance_category("History") is False
        assert is_en_stub_or_maintenance_category("Category:Science") is False


class TestCategoryDetection:
    """Test the category detection functionality."""

    def test_category_found_arabic(self) -> None:
        """Arabic category syntax should be detected."""
        text = "Some article text\n[[تصنيف:تاريخ]]\n"
        assert category_in_text(text, "تاريخ") is True

    def test_category_found_with_spaces(self) -> None:
        """Category with surrounding spaces should be detected."""
        text = "Some article text\n[[تصنيف: علم الفلك ]]\n"
        assert category_in_text(text, "علم الفلك") is True

    def test_category_not_found(self) -> None:
        """Missing category should not be detected."""
        text = "Some article text\n[[تصنيف:تاريخ]]\n"
        assert category_in_text(text, "علوم") is False

    def test_category_found_english_syntax(self) -> None:
        """English category syntax should be detected."""
        text = "Some article text\n[[Category:History]]\n"
        assert category_in_text(text, "History") is True

    def test_category_with_sort_key(self) -> None:
        """Category with sort key should be detected."""
        text = "Some article text\n[[تصنيف:تاريخ|مفتاح]]\n"
        assert category_in_text(text, "تاريخ") is True

    def test_category_case_insensitive(self) -> None:
        """Category detection should be case insensitive."""
        text = "Some article text\n[[category:History]]\n"
        assert category_in_text(text, "History") is True

    def test_multiple_categories(self) -> None:
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

    def test_empty_text(self) -> None:
        """Empty text should not match any category."""
        assert category_in_text("", "تاريخ") is False

    def test_category_in_middle_of_text(self) -> None:
        """Category should be detected even if not at the end."""
        text = (
            "Article beginning\n"
            "[[تصنيف:تاريخ]]\n"
            "More article text here\n"
        )

        assert category_in_text(text, "تاريخ") is True
