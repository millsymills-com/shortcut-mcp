from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"


@pytest.mark.asyncio
@respx.mock
async def test_list_groups_shapes_rows(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/groups").mock(
        return_value=httpx.Response(200, json=[{"id": "g1", "name": "Team", "mention_name": "team", "drop": 1}])
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_groups", {})
    assert not result.is_error
    assert result.data["items"][0] == {"id": "g1", "name": "Team", "mention_name": "team"}
    assert result.data["truncated"] is False


@pytest.mark.asyncio
@respx.mock
async def test_get_group_returns_full_object(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/groups/g1").mock(return_value=httpx.Response(200, json={"id": "g1"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_group", {"group_id": "g1"})
    assert not result.is_error
    assert result.data["id"] == "g1"


@pytest.mark.asyncio
@respx.mock
async def test_list_group_stories_shapes_rows(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/groups/g1/stories").mock(
        return_value=httpx.Response(200, json=[{"id": 50, "name": "S", "drop": 1}])
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_group_stories", {"group_id": "g1"})
    assert not result.is_error
    assert result.data["items"] == [{"id": 50, "name": "S"}]
    assert result.data["truncated"] is False
