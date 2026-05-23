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
async def test_list_epics_shapes_rows(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/epics").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "E", "description": "drop"}])
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_epics", {})
    assert not result.is_error
    assert result.data["items"] == [{"id": 1, "name": "E"}]
    assert result.data["truncated"] is False


@pytest.mark.asyncio
@respx.mock
async def test_get_epic_returns_full_object(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/epics/42").mock(return_value=httpx.Response(200, json={"id": 42, "name": "E"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_epic", {"epic_id": 42})
    assert not result.is_error
    assert result.data["id"] == 42


@pytest.mark.asyncio
@respx.mock
async def test_list_epics_raises_on_empty_body(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/epics").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_epics", {}, raise_on_error=False)
    assert result.is_error


@pytest.mark.asyncio
@respx.mock
async def test_list_epic_stories_shapes_rows(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/epics/7/stories").mock(
        return_value=httpx.Response(
            200, json=[{"id": 5, "name": "S", "story_type": "feature", "workflow_state_id": 1, "description": "drop"}]
        )
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_epic_stories", {"epic_id": 7})
    assert not result.is_error
    assert result.data["items"][0]["id"] == 5
    assert result.data["truncated"] is False


# ---------------------------------------------------------------------------
# Write tool tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_create_epic_posts_and_returns_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.post(f"{BASE}/epics").mock(return_value=httpx.Response(201, json={"id": 1, "name": "My Epic"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_create_epic", {"name": "My Epic"})
    assert not result.is_error
    assert result.data["id"] == 1
    body = json.loads(route.calls.last.request.content)
    assert body["name"] == "My Epic"


@pytest.mark.asyncio
@respx.mock
async def test_update_epic_returns_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.put(f"{BASE}/epics/1").mock(return_value=httpx.Response(200, json={"id": 1}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_epic", {"epic_id": 1, "name": "Updated"})
    assert not result.is_error
    assert result.data["id"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_update_epic_tolerates_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.put(f"{BASE}/epics/1").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_epic", {"epic_id": 1, "name": "Updated"})
    assert not result.is_error
    assert result.data["id"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_archive_epic_puts_archived_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.put(f"{BASE}/epics/1").mock(return_value=httpx.Response(200, json={"id": 1, "archived": True}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_archive_epic", {"epic_id": 1})
    assert not result.is_error
    body = json.loads(route.calls.last.request.content)
    assert body == {"archived": True}


@pytest.mark.asyncio
@respx.mock
async def test_unarchive_epic_puts_archived_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.put(f"{BASE}/epics/1").mock(return_value=httpx.Response(200, json={"id": 1, "archived": False}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_unarchive_epic", {"epic_id": 1})
    assert not result.is_error
    body = json.loads(route.calls.last.request.content)
    assert body == {"archived": False}
