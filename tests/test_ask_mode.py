#!/usr/bin/env python3
"""
"""

import pytest


class TestAskMode:
    """Test the interactive confirmation mode functionality."""

    def test_set_ask_mode(self):
        """Ask mode should be enabled and disabled correctly."""
        from unused_categories_bot import set_ask_mode, is_ask_mode

        set_ask_mode(False)
        assert is_ask_mode() is False

        set_ask_mode(True)
        assert is_ask_mode() is True

        set_ask_mode(False)
        assert is_ask_mode() is False

    def test_confirm_edit_without_ask_mode(self):
        """confirm_edit should return True when ask mode is disabled."""
        from unused_categories_bot import confirm_edit, set_ask_mode

        set_ask_mode(False)
        result = confirm_edit("Test Page", "old text", "new text")

        assert result is True

    def test_confirm_edit_with_yes_response(self, monkeypatch):
        """confirm_edit should return True when user enters 'y'."""
        import unused_categories_bot
        from unused_categories_bot import confirm_edit, set_ask_mode

        unused_categories_bot._auto_approve_all = False
        set_ask_mode(True)

        monkeypatch.setattr("builtins.input", lambda _: "y")

        result = confirm_edit("Test Page", "old text", "new text")
        assert result is True

        set_ask_mode(False)

    def test_confirm_edit_with_empty_response(self, monkeypatch):
        """confirm_edit should return True when user enters empty string."""
        import unused_categories_bot
        from unused_categories_bot import confirm_edit, set_ask_mode

        unused_categories_bot._auto_approve_all = False
        set_ask_mode(True)

        monkeypatch.setattr("builtins.input", lambda _: "")

        result = confirm_edit("Test Page", "old text", "new text")
        assert result is True

        set_ask_mode(False)

    def test_confirm_edit_with_no_response(self, monkeypatch):
        """confirm_edit should return False when user enters 'n'."""
        import unused_categories_bot
        from unused_categories_bot import confirm_edit, set_ask_mode

        unused_categories_bot._auto_approve_all = False
        set_ask_mode(True)

        monkeypatch.setattr("builtins.input", lambda _: "n")

        result = confirm_edit("Test Page", "old text", "new text")
        assert result is False

        set_ask_mode(False)

    def test_confirm_edit_with_all_response(self, monkeypatch):
        """Entering 'a' should enable auto_approve_all."""
        import unused_categories_bot
        from unused_categories_bot import confirm_edit, set_ask_mode

        unused_categories_bot._auto_approve_all = False
        set_ask_mode(True)

        monkeypatch.setattr("builtins.input", lambda _: "a")

        result = confirm_edit("Test Page", "old text", "new text")

        assert result is True
        assert unused_categories_bot._auto_approve_all is True

        unused_categories_bot._auto_approve_all = False
        set_ask_mode(False)

    def test_confirm_edit_auto_approve_skips_prompt(self, monkeypatch):
        """input() should not be called when auto_approve_all is True."""
        import unused_categories_bot
        from unused_categories_bot import confirm_edit, set_ask_mode

        unused_categories_bot._auto_approve_all = True
        set_ask_mode(True)

        def fail_if_called(*args, **kwargs):
            raise AssertionError("input() should not be called")

        monkeypatch.setattr("builtins.input", fail_if_called)

        result = confirm_edit("Test Page", "old text", "new text")
        assert result is True

        unused_categories_bot._auto_approve_all = False
        set_ask_mode(False)
