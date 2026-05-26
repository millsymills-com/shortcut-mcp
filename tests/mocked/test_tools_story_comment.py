from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"


@pytest.mark.asyncio
@respx.mock
async def test_list_story_comments_shapes_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/stories/5/comments").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": 3, "text": "hi", "author_id": "a", "drop": 1}],
        )
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_story_comments", {"story_id": 5})
    assert not result.is_error
    assert result.data["items"][0]["id"] == 3
    assert result.data["truncated"] is False


@pytest.mark.asyncio
@respx.mock
async def test_get_story_comment_returns_full_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/stories/5/comments/3").mock(return_value=httpx.Response(200, json={"id": 3}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_story_comment", {"story_id": 5, "comment_id": 3})
    assert not result.is_error
    assert result.data["id"] == 3
