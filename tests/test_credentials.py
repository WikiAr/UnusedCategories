#!/usr/bin/env python3
"""
Tests for credential loading functionality.
"""

import pytest


class TestCredentialLoading:
    """Test credential loading functionality."""

    def test_credentials_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that missing credentials raises an error."""
        from unused_categories_bot import load_credentials
        from utils.exceptions import CredentialError

        monkeypatch.delenv("WIKI_BOT_USERNAME", raising=False)
        monkeypatch.delenv("WIKI_BOT_PASSWORD", raising=False)

        # Accept either ValueError (old) or CredentialError (new)
        with pytest.raises((ValueError, CredentialError)):
            load_credentials()

    def test_credentials_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that credentials are loaded correctly."""
        from unused_categories_bot import load_credentials

        monkeypatch.setenv("WIKI_BOT_USERNAME", "test_user")
        monkeypatch.setenv("WIKI_BOT_PASSWORD", "test_pass")

        username, password = load_credentials()

        assert username == "test_user"
        assert password == "test_pass"
