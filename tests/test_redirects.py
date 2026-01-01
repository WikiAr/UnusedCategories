#!/usr/bin/env python3
"""
"""


class RedirectPage:
    def redirects_to(self) -> None:
        return object()


class NormalPage:
    def redirects_to(self) -> None:
        return None


class ErrorRedirectPage:
    def __init__(self, exc):
        self.name = "Error Page"
        self._exc = exc

    def redirects_to(self) -> None:
        raise self._exc


class TestRedirectPageCheck:
    """Test the redirect page check functionality."""

    def test_redirect_page_detected(self) -> None:
        from unused_categories_bot import is_redirect_page
        page = RedirectPage()
        assert is_redirect_page(page) is True

    def test_non_redirect_page_not_flagged(self) -> None:
        from unused_categories_bot import is_redirect_page

        page = NormalPage()
        assert is_redirect_page(page) is False

    def test_redirect_check_handles_api_error(self) -> None:
        from unused_categories_bot import is_redirect_page
        import mwclient.errors

        page = ErrorRedirectPage(
            mwclient.errors.APIError("error", "info", {})
        )

        assert is_redirect_page(page) is False

    def test_add_category_skips_redirect_page(self) -> None:
        from unused_categories_bot import add_category_to_page

        class Page:
            name = "Redirect Page"

            def redirects_to(self) -> None:
                return object()

            def text(self) -> None:
                raise AssertionError("text() should not be called")

            def save(self, *args, **kwargs):
                raise AssertionError("save() should not be called")

        page = Page()

        result = add_category_to_page(page, "TestCategory", "summary")

        assert result is False
