# Tests for has_ar_category_redirect_template function.

import pytest

from src.utils import has_ar_category_redirect_template


class TestHasArCategoryRedirectTemplate:
    """Tests for has_ar_category_redirect_template function."""

    def test_template_present(self) -> None:
        """Test when the template is present in the text."""
        text = "هذا نص المقالة\n{{تحويل تصنيف|تصنيف قديم|تصنيف جديد}}\nالمزيد من النص"
        assert has_ar_category_redirect_template(text) is True

    def test_template_absent(self) -> None:
        """Test when the template is absent in the text."""
        text = "هذا نص المقالة\nلا يوجد هنا أي قالب تحويل تصنيف.\nالمزيد من النص"
        assert has_ar_category_redirect_template(text) is False

    def test_template_with_spaces(self) -> None:
        """Test when the template has extra spaces."""
        text = "هذا نص المقالة\n{{  تحويل تصنيف  | تصنيف قديم | تصنيف جديد  }}\nالمزيد من النص"
        assert has_ar_category_redirect_template(text) is True

    def test_multiple_templates(self) -> None:
        """Test when multiple templates are present."""
        text = (
            "هذا نص المقالة\n"
            "{{تحويل تصنيف|تصنيف قديم1|تصنيف جديد1}}\n"
            "نص إضافي\n"
            "{{تحويل تصنيف|تصنيف قديم2|تصنيف جديد2}}\n"
            "المزيد من النص"
        )
        assert has_ar_category_redirect_template(text) is True
