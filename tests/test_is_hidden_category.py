#!/usr/bin/env python3
"""
"""


class FakeSite:
    def __init__(self, response):
        self._response = response
        self.called_with = None

    def get(self, *args, **kwargs):
        self.called_with = (args, kwargs)
        return self._response


class FakePage:
    def __init__(self, name, site):
        self.name = name
        self.site = site


class TestHiddenCategoryCheck:
    """Test the hidden category check functionality."""

    def test_hidden_category_detected(self) -> None:
        from unused_categories_bot import is_hidden_category

        site = FakeSite({
            "query": {
                "pages": {
                    "123": {
                        "categoryinfo": {"hidden": True}
                    }
                }
            }
        })

        page = FakePage("Category:Hidden test", site)

        assert is_hidden_category(page) is True

    def test_visible_category_not_flagged(self) -> None:
        from unused_categories_bot import is_hidden_category

        site = FakeSite({
            "query": {
                "pages": {
                    "123": {
                        "categoryinfo": {"hidden": False}
                    }
                }
            }
        })

        page = FakePage("Category:Visible test", site)

        assert is_hidden_category(page) is False

    def test_category_without_categoryinfo(self) -> None:
        from unused_categories_bot import is_hidden_category

        site = FakeSite({
            "query": {
                "pages": {
                    "123": {}
                }
            }
        })

        page = FakePage("Category:Test", site)

        assert is_hidden_category(page) is False
