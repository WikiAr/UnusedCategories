
import pytest

from utils import (
    en_page_has_category_in_text,
)


class TestEnPageHasCategoryInText:
    """Tests for en_page_has_category_in_text function."""

    def test_category_with_prefix(self) -> None:
        """Test finding category when name includes prefix."""
        text = "Article text\n[[Category:Science]]"
        assert en_page_has_category_in_text(text, 'Category:Science')

    def test_category_without_prefix(self) -> None:
        """Test finding category when name doesn't include prefix."""
        text = "Article text\n[[Category:Science]]"
        assert en_page_has_category_in_text(text, 'Science')

    def test_category_with_sort_key(self) -> None:
        """Test finding category with sort key."""
        text = "[[Category:Science|Sort key]]"
        assert en_page_has_category_in_text(text, 'Science')

    def test_category_with_spaces(self) -> None:
        """Test finding category with spaces."""
        text = "[[ Category : Science ]]"
        assert en_page_has_category_in_text(text, 'Science')

    def test_category_not_found(self) -> None:
        """Test when category is not in text."""
        text = "Article text\n[[Category:Mathematics]]"
        assert not en_page_has_category_in_text(text, 'Science')

    def test_case_insensitive_match(self) -> None:
        """Test case-insensitive matching."""
        text = "[[Category:SCIENCE]]"
        assert en_page_has_category_in_text(text, 'Science')
        assert en_page_has_category_in_text(text, 'science')

    def test_multiple_categories(self) -> None:
        """Test finding specific category among multiple categories."""
        text = "[[Category:Science]]\n[[Category:Mathematics]]\n[[Category:Physics]]"
        assert en_page_has_category_in_text(text, 'Science')
        assert en_page_has_category_in_text(text, 'Mathematics')
        assert not en_page_has_category_in_text(text, 'Chemistry')

    def test_en_page_has_category_in_text_found(self) -> None:
        text = "Article text\n[[Category:History]]\nMore text"

        assert en_page_has_category_in_text(text, "History") is True
        assert en_page_has_category_in_text(text, "Category:History") is True

    def test_en_page_has_category_in_text_not_found(self) -> None:
        text = "Article text\n[[Category:Science]]\nMore text"

        assert en_page_has_category_in_text(text, "History") is False

    def test_en_page_has_category_with_sort_key(self) -> None:
        text = "Article text\n[[Category:History|Key]]\nMore text"

        assert en_page_has_category_in_text(text, "History") is True

    def test_en_page_has_category_case_insensitive(self) -> None:
        text = "Article text\n[[category:history]]\nMore text"

        assert en_page_has_category_in_text(text, "History") is True


def test_special_case() -> None:
    """Test category names with special regex characters."""
    text = (
        "{{Portal|North America|Association football|{{FindYDCportal|{{Title year}}}}|Countries}}\n"
        "{{Category series navigation}}\n"
        "[[Category:{{Title year range}} in North American football| ]]\n"
        "[[Category:{{Title year range}} in association football by country|North American]]\n"
        "[[Category:Association football in North America by season and country]]"
    )
    page_title = "Category:1951–52 in North American football by country"
    assert en_page_has_category_in_text(text, "Category:1951–52 in North American football", page_title) is True


def test_special_case_year() -> None:
    """Test category names with special regex characters."""
    text = (
        "{{Portal|North America|Association football|{{FindYDCportal|{{Title year}}}}|Countries}}\n"
        "{{Category series navigation}}\n"
        "[[Category:{{Title year range}} in North American football| ]]\n"
        "[[Category:{{Title year range}} in association football by country|North American]]\n"
        "[[Category:Association football in North America by season and country]]"
    )
    page_title = "Category:1951 in North American football by country"
    assert en_page_has_category_in_text(text, "Category:1951 in North American football", page_title) is True
