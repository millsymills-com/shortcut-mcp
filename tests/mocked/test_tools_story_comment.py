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


# ---------------------------------------------------------------------------
# Write tool tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_create_story_comment_posts_and_returns_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.post(f"{BASE}/stories/5/comments").mock(
        return_value=httpx.Response(201, json={"id": 3, "text": "hello"})
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_create_story_comment", {"story_id": 5, "text": "hello"})
    assert not result.is_error
    assert result.data["id"] == 3
    body = json.loads(route.calls.last.request.content)
    assert body["text"] == "hello"


@pytest.mark.asyncio
@respx.mock
async def test_update_story_comment_returns_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.put(f"{BASE}/stories/5/comments/3").mock(return_value=httpx.Response(200, json={"id": 3}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_update_story_comment", {"story_id": 5, "comment_id": 3, "text": "updated"}
        )
    assert not result.is_error
    assert result.data["id"] == 3


@pytest.mark.asyncio
@respx.mock
async def test_add_story_comment_reaction_sends_emoji(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.post(f"{BASE}/stories/5/comments/3/reactions").mock(return_value=httpx.Response(200, json={}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_add_story_comment_reaction", {"story_id": 5, "comment_id": 3, "emoji": "x"}
        )
    assert not result.is_error
    body = json.loads(route.calls.last.request.content)
    assert body == {"emoji": "x"}


@pytest.mark.asyncio
@respx.mock
async def test_remove_story_comment_reaction_sends_delete_with_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/stories/5/comments/3/reactions").mock(return_value=httpx.Response(200, json={}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_remove_story_comment_reaction", {"story_id": 5, "comment_id": 3, "emoji": "x"}
        )
    assert not result.is_error
    body = json.loads(route.calls.last.request.content)
    assert body == {"emoji": "x"}
