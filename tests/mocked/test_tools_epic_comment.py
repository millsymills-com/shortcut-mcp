from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"


@pytest.mark.asyncio
@respx.mock
async def test_list_epic_comments_shapes_rows(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/epics/7/comments").mock(
        return_value=httpx.Response(200, json=[{"id": 11, "text": "hi", "author_id": "a"}])
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_epic_comments", {"epic_id": 7})
    assert not result.is_error
    assert result.data["items"][0]["id"] == 11
    assert result.data["truncated"] is False


@pytest.mark.asyncio
@respx.mock
async def test_get_epic_comment_returns_full_object(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/epics/7/comments/11").mock(return_value=httpx.Response(200, json={"id": 11, "text": "hi"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_epic_comment", {"epic_id": 7, "comment_id": 11})
    assert not result.is_error
    assert result.data["id"] == 11
