from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"


def _destructive_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("tool", "endpoint", "expected"),
    [
        ("shortcut_enable_iterations", "/iterations/enable", {"feature": "iterations", "enabled": True}),
        ("shortcut_disable_iterations", "/iterations/disable", {"feature": "iterations", "enabled": False}),
        (
            "shortcut_enable_story_templates",
            "/entity-templates/enable",
            {"feature": "story_templates", "enabled": True},
        ),
        (
            "shortcut_disable_story_templates",
            "/entity-templates/disable",
            {"feature": "story_templates", "enabled": False},
        ),
    ],
)
async def test_toggle_hits_endpoint(
    monkeypatch: pytest.MonkeyPatch, tool: str, endpoint: str, expected: dict[str, object]
) -> None:
    _destructive_env(monkeypatch)
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.put(f"{BASE}{endpoint}").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(tool, {})
    assert not result.is_error
    assert result.data == expected
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_toggles_gated_at_destructive_tier(monkeypatch: pytest.MonkeyPatch) -> None:
    # readwrite WITHOUT allow-destructive: toggles must stay hidden.
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    server = create_server()
    async with Client(server) as client:
        names = {t.name for t in await client.list_tools()}
    assert "shortcut_enable_iterations" not in names
    assert "shortcut_disable_story_templates" not in names


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("tool", "endpoint"),
    [
        ("shortcut_enable_iterations", "/iterations/enable"),
        ("shortcut_disable_iterations", "/iterations/disable"),
        ("shortcut_enable_story_templates", "/entity-templates/enable"),
        ("shortcut_disable_story_templates", "/entity-templates/disable"),
    ],
)
async def test_toggle_runtime_guard_blocks_without_destructive(
    monkeypatch: pytest.MonkeyPatch, tool: str, endpoint: str
) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.put(f"{BASE}{endpoint}").mock(return_value=httpx.Response(204))
    server = create_server()
    # Re-enable the tag the visibility gate stripped, so the call reaches the
    # in-body require_destructive() guard instead of failing at "unknown tool".
    server.enable(tags={"destructive"})
    async with Client(server) as client:
        result = await client.call_tool(tool, {}, raise_on_error=False)
    assert result.is_error
    assert "mode_denied" in result.content[0].text
    assert not route.called
