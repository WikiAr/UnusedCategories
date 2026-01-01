#!/usr/bin/env python3
"""
"""

import pytest


class TestCredentialLoading:
    """Test credential loading functionality."""

    def test_credentials_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from unused_categories_bot import load_credentials

        monkeypatch.delenv("WM_USERNAME", raising=False)
        monkeypatch.delenv("PASSWORD", raising=False)

        with pytest.raises(ValueError):
            load_credentials()

    def test_credentials_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from unused_categories_bot import load_credentials

        monkeypatch.setenv("WM_USERNAME", "test_user")
        monkeypatch.setenv("PASSWORD", "test_pass")

        username, password = load_credentials()

        assert username == "test_user"
        assert password == "test_pass"
