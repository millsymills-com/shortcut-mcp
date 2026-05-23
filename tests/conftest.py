"""Shared pytest fixtures."""

from __future__ import annotations

import os

import pytest

from shortcut_mcp.config import ShortcutConfig


@pytest.fixture
def fake_config(monkeypatch: pytest.MonkeyPatch) -> ShortcutConfig:
    """A valid config with a fake token. Use for mocked tests."""
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "fake-token-for-tests")
    monkeypatch.setenv("SHORTCUT_MODE", "readonly")
    return ShortcutConfig()


@pytest.fixture
def live_token() -> str:
    """Real token from env. Tests using this should mark live + smoke."""
    token = os.environ.get("SHORTCUT_API_TOKEN")
    if not token:
        pytest.skip("SHORTCUT_API_TOKEN not set; skipping live test")
    return token
