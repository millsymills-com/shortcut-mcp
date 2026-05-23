"""Unit tests for ShortcutConfig."""

from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from shortcut_mcp.config import ALL_MODULES, ShortcutConfig, ShortcutMode, ToolProfile


def test_loads_token_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "test-token-xyz")
    config = ShortcutConfig()
    assert isinstance(config.shortcut_api_token, SecretStr)
    assert config.shortcut_api_token.get_secret_value() == "test-token-xyz"


def test_authenticated_property(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHORTCUT_API_TOKEN", raising=False)
    assert ShortcutConfig().authenticated is False
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    assert ShortcutConfig().authenticated is True


def test_writes_disabled_in_readonly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    config = ShortcutConfig()
    assert config.shortcut_mode is ShortcutMode.READONLY
    assert config.writes_enabled is False
    assert config.destructive_enabled is False


def test_writes_enabled_in_readwrite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    config = ShortcutConfig()
    assert config.writes_enabled is True
    assert config.destructive_enabled is False  # allow-destructive still false


def test_destructive_requires_both_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    assert ShortcutConfig().destructive_enabled is True


def test_destructive_blocked_in_readonly_even_if_allow_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    # mode stays readonly default
    assert ShortcutConfig().destructive_enabled is False


def test_config_is_frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    config = ShortcutConfig()
    with pytest.raises(ValidationError):
        config.shortcut_mode = ShortcutMode.READWRITE  # type: ignore[misc]


def test_default_profile_is_core(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    cfg = ShortcutConfig()
    assert cfg.shortcut_profile is ToolProfile.CORE
    assert "story" in cfg.enabled_modules
    assert "project" not in cfg.enabled_modules  # planning-only


def test_profile_all_enables_every_module(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    cfg = ShortcutConfig()
    assert cfg.enabled_modules == ALL_MODULES


def test_explicit_tools_override_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    monkeypatch.setenv("SHORTCUT_TOOLS", "story, epic")
    cfg = ShortcutConfig()
    assert cfg.enabled_modules == {"story", "epic"}


def test_unknown_tool_name_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_TOOLS", "story, bogus")
    with pytest.raises(ValidationError, match="bogus"):
        ShortcutConfig()
