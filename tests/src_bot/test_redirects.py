#!/usr/bin/env python3
""" """


class RedirectPage:
    def redirects_to(self) -> None:
        return object()  # pyright: ignore[reportReturnType]


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
        from src.src_bot.unused_categories_bot import is_redirect_page

        page = RedirectPage()
        assert is_redirect_page(page) is True  # pyright: ignore[reportArgumentType]

    def test_non_redirect_page_not_flagged(self) -> None:
        from src.src_bot.unused_categories_bot import is_redirect_page

        page = NormalPage()
        assert is_redirect_page(page) is False  # pyright: ignore[reportArgumentType]

    def test_redirect_check_handles_api_error(self) -> None:
        import mwclient.errors

        from src.src_bot.unused_categories_bot import is_redirect_page

        page = ErrorRedirectPage(mwclient.errors.APIError("error", "info", {}))

        assert is_redirect_page(page) is False  # pyright: ignore[reportArgumentType]

    def test_add_category_skips_redirect_page(self) -> None:
        from src.src_bot.unused_categories_bot import add_category_to_page

        class Page:
            name = "Redirect Page"

            def redirects_to(self) -> None:
                return object()  # pyright: ignore[reportReturnType]

            def text(self) -> None:
                raise AssertionError("text() should not be called")

            def save(self, *args, **kwargs):
                raise AssertionError("save() should not be called")

        page = Page()

        result = add_category_to_page(page, "TestCategory", "summary")  # pyright: ignore[reportArgumentType]

        assert result is False
