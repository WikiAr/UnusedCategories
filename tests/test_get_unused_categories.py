#!/usr/bin/env python3
"""
"""

import pytest


class FakeSite:
    def __init__(self, response) -> None:
        self._response = response
        self.called_with = None

    def get(self, *args, **kwargs):
        self.called_with = (args, kwargs)
        return self._response


class TestGetUnusedCategories:
    """Test the unused categories fetching functionality."""

    def test_get_unused_categories_returns_results(self) -> None:
        from unused_categories_bot import get_unused_categories

        site = FakeSite({
            "query": {
                "querypage": {
                    "name": "Unusedcategories",
                    "results": [
                        {"title": "تصنيف:تاريخ", "ns": 14},
                        {"title": "تصنيف:علوم", "ns": 14},
                    ],
                }
            }
        })

        categories = get_unused_categories(site, limit=10)

        assert site.called_with == (
            ("query",),
            {
                "list": "querypage",
                "qppage": "Unusedcategories",
                "qplimit": 10,
            },
        )

        assert len(categories) == 2
        assert categories[0] == "تصنيف:تاريخ", str(categories)
        assert categories[1] == "تصنيف:علوم", str(categories)

    def test_get_unused_categories_empty_results(self) -> None:
        from unused_categories_bot import get_unused_categories

        site = FakeSite({
            "query": {
                "querypage": {
                    "name": "Unusedcategories",
                    "results": [],
                }
            }
        })

        categories = get_unused_categories(site, limit=10)
        assert categories == []

    def test_get_unused_categories_missing_query(self) -> None:
        from unused_categories_bot import get_unused_categories

        site = FakeSite({})
        categories = get_unused_categories(site, limit=10)

        assert categories == []
