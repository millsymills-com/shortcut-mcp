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


# ---------------------------------------------------------------------------
# Write tool tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_create_epic_comment_posts_and_returns_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.post(f"{BASE}/epics/1/comments").mock(
        return_value=httpx.Response(201, json={"id": 3, "text": "hello"})
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_create_epic_comment", {"epic_id": 1, "text": "hello"})
    assert not result.is_error
    assert result.data["id"] == 3
    body = json.loads(route.calls.last.request.content)
    assert body["text"] == "hello"


@pytest.mark.asyncio
@respx.mock
async def test_create_epic_comment_reply_posts_to_comment_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.post(f"{BASE}/epics/1/comments/3").mock(
        return_value=httpx.Response(201, json={"id": 4, "text": "reply"})
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_create_epic_comment_reply", {"epic_id": 1, "comment_id": 3, "text": "reply"}
        )
    assert not result.is_error
    assert result.data["id"] == 4
    body = json.loads(route.calls.last.request.content)
    assert body["text"] == "reply"
    assert str(route.calls.last.request.url).endswith("/epics/1/comments/3")


@pytest.mark.asyncio
@respx.mock
async def test_update_epic_comment_returns_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.put(f"{BASE}/epics/1/comments/3").mock(return_value=httpx.Response(200, json={"id": 3}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_update_epic_comment", {"epic_id": 1, "comment_id": 3, "text": "updated"}
        )
    assert not result.is_error
    assert result.data["id"] == 3


@pytest.mark.asyncio
@respx.mock
async def test_delete_epic_comment_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/epics/12/comments/8").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_epic_comment", {"epic_id": 12, "comment_id": 8})
    assert not result.is_error
    assert result.data == {"id": 8, "deleted": True}
    assert route.called
