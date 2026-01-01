
import pytest

from utils import (
    _build_category_pattern,
    category_in_text,
    is_ar_stub_or_maintenance_category,
    is_en_stub_or_maintenance_category
)


@pytest.mark.fast
class TestBuildCategoryPattern:
    """Tests for _build_category_pattern function."""

    def test_simple_category_pattern(self) -> None:
        """Test building a simple category pattern."""
        pattern = _build_category_pattern('Test', 'Category')
        assert 'Category' in pattern
        assert 'Test' in pattern

    def test_arabic_category_pattern(self) -> None:
        """Test building an Arabic category pattern."""
        pattern = _build_category_pattern('علوم', 'تصنيف')
        assert 'تصنيف' in pattern
        assert 'علوم' in pattern

    def test_category_with_special_chars(self) -> None:
        """Test building a pattern with special regex characters."""
        pattern = _build_category_pattern('Test (something)', 'Category')
        # Should escape special characters like parentheses
        assert r'\(' in pattern
        assert r'\)' in pattern


class TestCategoryInText:
    """Tests for category_in_text function."""

    def test_arabic_category_found(self) -> None:
        """Test finding an Arabic category in text."""
        text = "هذا نص المقالة\n[[تصنيف:علوم]]"
        assert category_in_text(text, 'علوم')

    def test_english_category_found(self) -> None:
        """Test finding an English category in Arabic text."""
        text = "هذا نص المقالة\n[[Category:Science]]"
        assert category_in_text(text, 'Science')

    def test_category_with_spaces(self) -> None:
        """Test finding category with spaces around colons."""
        text = "[[تصنيف : علوم]]"
        assert category_in_text(text, 'علوم')

    def test_category_with_sort_key(self) -> None:
        """Test finding category with sort key."""
        text = "[[تصنيف:علوم|مفتاح الترتيب]]"
        assert category_in_text(text, 'علوم')

    def test_category_not_found(self) -> None:
        """Test when category is not in text."""
        text = "هذا نص المقالة\n[[تصنيف:رياضيات]]"
        assert not category_in_text(text, 'علوم')

    def test_case_insensitive_match(self) -> None:
        """Test case-insensitive matching."""
        text = "[[Category:SCIENCE]]"
        assert category_in_text(text, 'Science')
        assert category_in_text(text, 'science')

    def test_category_in_link_text(self) -> None:
        """Test that category in regular text is not matched."""
        text = "This article is about علوم but has no category"
        assert not category_in_text(text, 'علوم')

    def test_multiple_categories(self) -> None:
        """Test finding specific category among multiple categories."""
        text = "[[تصنيف:علوم]]\n[[تصنيف:رياضيات]]\n[[تصنيف:فيزياء]]"
        assert category_in_text(text, 'علوم')
        assert category_in_text(text, 'رياضيات')
        assert category_in_text(text, 'فيزياء')


class TestIsArStubOrMaintenanceCategory:
    """Tests for is_ar_stub_or_maintenance_category function."""

    def test_stub_category_with_prefix(self) -> None:
        """Test stub category starting with بذرة (with prefix)."""
        assert is_ar_stub_or_maintenance_category('تصنيف:بذرة علوم')

    def test_stub_category_without_prefix(self) -> None:
        """Test stub category starting with بذرة (without prefix)."""
        assert is_ar_stub_or_maintenance_category('بذرة رياضيات')

    def test_stubs_category(self) -> None:
        """Test category containing بذور (stubs plural)."""
        assert is_ar_stub_or_maintenance_category('بذور العلوم')
        assert is_ar_stub_or_maintenance_category('تصنيف:بذور الرياضيات')

    def test_maintenance_category(self) -> None:
        """Test maintenance category containing صيانة."""
        assert is_ar_stub_or_maintenance_category('تصنيف:صيانة المقالات')
        assert is_ar_stub_or_maintenance_category('صيانة')

    def test_regular_category(self) -> None:
        """Test regular category (not stub or maintenance)."""
        assert not is_ar_stub_or_maintenance_category('علوم')
        assert not is_ar_stub_or_maintenance_category('تصنيف:رياضيات')
        assert not is_ar_stub_or_maintenance_category('تصنيف:فيزياء')

    def test_category_with_stub_in_middle(self) -> None:
        """Test that بذور is detected anywhere in the name."""
        assert is_ar_stub_or_maintenance_category('مقالات بذور')

    def test_category_with_maintenance_in_middle(self) -> None:
        """Test that صيانة is detected anywhere in the name."""
        assert is_ar_stub_or_maintenance_category('مقالات صيانة منذ 2020')


class TestIsEnStubOrMaintenanceCategory:
    """Tests for is_en_stub_or_maintenance_category function."""

    def test_stub_category_lowercase(self) -> None:
        """Test stub category with lowercase 'stub'."""
        assert is_en_stub_or_maintenance_category('Science stubs')

    def test_stub_category_uppercase(self) -> None:
        """Test stub category with uppercase 'STUB'."""
        assert is_en_stub_or_maintenance_category('SCIENCE STUBS')

    def test_stub_category_mixed_case(self) -> None:
        """Test stub category with mixed case."""
        assert is_en_stub_or_maintenance_category('Category:Science Stub')

    def test_maintenance_category_lowercase(self) -> None:
        """Test maintenance category with lowercase 'maintenance'."""
        assert is_en_stub_or_maintenance_category('Articles needing maintenance')

    def test_maintenance_category_uppercase(self) -> None:
        """Test maintenance category with uppercase 'MAINTENANCE'."""
        assert is_en_stub_or_maintenance_category('MAINTENANCE CATEGORIES')

    def test_maintenance_category_with_prefix(self) -> None:
        """Test maintenance category with Category: prefix."""
        assert is_en_stub_or_maintenance_category('Category:Wikipedia maintenance')

    def test_regular_category(self) -> None:
        """Test regular category (not stub or maintenance)."""
        assert not is_en_stub_or_maintenance_category('Science')
        assert not is_en_stub_or_maintenance_category('Category:Mathematics')
        assert not is_en_stub_or_maintenance_category('Physics')

    def test_category_with_stub_substring(self) -> None:
        """Test that 'stub' is detected as substring."""
        assert is_en_stub_or_maintenance_category('Stubborn categories')

    def test_stub_at_beginning(self) -> None:
        """Test stub at the beginning of category name."""
        assert is_en_stub_or_maintenance_category('Stub categories')
