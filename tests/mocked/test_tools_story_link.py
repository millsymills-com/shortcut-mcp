from __future__ import annotations

import json

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"


@pytest.mark.asyncio
@respx.mock
async def test_get_story_link_returns_full_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/story-links/4").mock(return_value=httpx.Response(200, json={"id": 4, "verb": "blocks"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_story_link", {"story_link_id": 4})
    assert not result.is_error
    assert result.data["id"] == 4


# ---------------------------------------------------------------------------
# Write tool tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_create_story_link_posts_and_returns_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.post(f"{BASE}/story-links").mock(return_value=httpx.Response(201, json={"id": 4, "verb": "blocks"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_create_story_link", {"verb": "blocks", "subject_id": 10, "object_id": 20}
        )
    assert not result.is_error
    assert result.data["id"] == 4
    body = json.loads(route.calls.last.request.content)
    assert body["verb"] == "blocks"
    assert body["subject_id"] == 10
    assert body["object_id"] == 20


@pytest.mark.asyncio
@respx.mock
async def test_update_story_link_returns_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.put(f"{BASE}/story-links/4").mock(return_value=httpx.Response(200, json={"id": 4, "verb": "duplicates"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_story_link", {"story_link_id": 4, "verb": "duplicates"})
    assert not result.is_error
    assert result.data["id"] == 4
