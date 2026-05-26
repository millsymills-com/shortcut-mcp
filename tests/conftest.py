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


@pytest.fixture
def live_write_token() -> str:
    """Isolated write/destructive workspace token. Skips unless explicitly opted in.

    Requires BOTH SHORTCUT_LIVE_WRITE_TESTS=true AND a token in
    SHORTCUT_TEST_WORKSPACE_TOKEN (deliberately NOT SHORTCUT_API_TOKEN, so the
    nightly read token can never be used to mutate or delete data).
    """
    if os.environ.get("SHORTCUT_LIVE_WRITE_TESTS", "").lower() != "true":
        pytest.skip("SHORTCUT_LIVE_WRITE_TESTS != true; skipping live write/destructive test")
    token = os.environ.get("SHORTCUT_TEST_WORKSPACE_TOKEN")
    if not token:
        pytest.skip("SHORTCUT_TEST_WORKSPACE_TOKEN not set; skipping live write/destructive test")
    return token
