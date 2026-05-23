"""Mocked tests for the shortcut_get_story tool.

FastMCP 3.3.1 invocation pattern (discovered in Task 13):
- `await server.get_tool(name)` returns a FunctionTool (it's async).
- `tool.fn` is the underlying coroutine function, but ctx is dependency-injected
  and cannot be constructed in isolation.
- The correct test pattern is `async with Client(server) as client:` which wires
  up the lifespan and injects ctx properly, then `result = await client.call_tool(name, args)`
  where `result.data` is the return value and `result.is_error` signals an error.
- For error propagation, the MCP surface serializes tool exceptions as error text.
  We verify ShortcutClientError reaches the caller by asserting `result.is_error`.
"""

from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server


@pytest.mark.asyncio
@respx.mock
async def test_get_story_returns_story_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get("https://api.app.shortcut.com/api/v3/member").mock(
        return_value=httpx.Response(200, json={"id": "user-1"})
    )
    respx.get("https://api.app.shortcut.com/api/v3/stories/1234").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 1234,
                "name": "Tracer bullet",
                "app_url": "https://app.shortcut.com/x/story/1234",
                "workflow_state_id": 500,
            },
        )
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_story", {"story_id": 1234})
    assert not result.is_error
    assert result.data["id"] == 1234
    assert result.data["name"] == "Tracer bullet"


@pytest.mark.asyncio
@respx.mock
async def test_get_story_propagates_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get("https://api.app.shortcut.com/api/v3/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get("https://api.app.shortcut.com/api/v3/stories/9999").mock(
        return_value=httpx.Response(404, json={"message": "not found"})
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_story", {"story_id": 9999}, raise_on_error=False)
    assert result.is_error


@pytest.mark.asyncio
@respx.mock
async def test_list_story_history_returns_items(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    base = "https://api.app.shortcut.com/api/v3"
    respx.get(f"{base}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{base}/stories/7/history").mock(return_value=httpx.Response(200, json=[{"id": "h1"}, {"id": "h2"}]))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_story_history", {"story_id": 7})
    assert not result.is_error
    assert result.data["items"][0]["id"] == "h1"
    assert result.data["truncated"] is False
