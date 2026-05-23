from __future__ import annotations

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
