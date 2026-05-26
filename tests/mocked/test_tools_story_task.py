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
async def test_get_story_task_returns_full_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/stories/5/tasks/9").mock(return_value=httpx.Response(200, json={"id": 9, "complete": False}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_story_task", {"story_id": 5, "task_id": 9})
    assert not result.is_error
    assert result.data["id"] == 9


# ---------------------------------------------------------------------------
# Write tool tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_create_story_task_posts_and_returns_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.post(f"{BASE}/stories/5/tasks").mock(
        return_value=httpx.Response(201, json={"id": 9, "description": "Do the thing"})
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_create_story_task", {"story_id": 5, "description": "Do the thing"})
    assert not result.is_error
    assert result.data["id"] == 9
    body = json.loads(route.calls.last.request.content)
    assert body["description"] == "Do the thing"


@pytest.mark.asyncio
@respx.mock
async def test_update_story_task_omits_none_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.put(f"{BASE}/stories/5/tasks/9").mock(
        return_value=httpx.Response(200, json={"id": 9, "complete": True})
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_story_task", {"story_id": 5, "task_id": 9, "complete": True})
    assert not result.is_error
    body = json.loads(route.calls.last.request.content)
    assert body == {"complete": True}
    assert "description" not in body


@pytest.mark.asyncio
@respx.mock
async def test_delete_story_task_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/stories/5/tasks/3").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_story_task", {"story_id": 5, "task_id": 3})
    assert not result.is_error
    assert result.data == {"id": 3, "deleted": True}
    assert route.called
