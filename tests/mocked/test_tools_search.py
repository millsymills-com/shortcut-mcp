from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"


@pytest.mark.asyncio
@respx.mock
async def test_search_stories_unwraps_data_envelope(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/search/stories").mock(
        return_value=httpx.Response(
            200, json={"data": [{"id": 1, "name": "A", "description": "drop"}], "next": None, "total": 1}
        )
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_search_stories", {"query": "state:done"})
    assert not result.is_error
    assert result.data["items"] == [{"id": 1, "name": "A"}]
    assert result.data["total"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_query_stories_uses_post(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.post(f"{BASE}/stories/search").mock(return_value=httpx.Response(200, json=[{"id": 9, "name": "Q"}]))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_query_stories", {"archived": False})
    assert not result.is_error
    assert result.data["items"][0]["id"] == 9


@pytest.mark.asyncio
@respx.mock
async def test_search_epics_routes_to_search_epics_endpoint(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/search/epics").mock(
        return_value=httpx.Response(200, json={"data": [{"id": 5, "name": "E"}], "next": None, "total": 1})
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_search_epics", {"query": "x"})
    assert not result.is_error
    assert result.data["items"] == [{"id": 5, "name": "E"}]


@pytest.mark.asyncio
@respx.mock
async def test_global_search_returns_stories_and_epics_shape(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/search").mock(
        return_value=httpx.Response(
            200,
            json={"stories": {"data": [{"id": 1, "name": "S"}]}, "epics": {"data": [{"id": 2, "name": "E"}]}},
        )
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_search", {"query": "x"})
    assert not result.is_error
    assert result.data["stories"]["items"] == [{"id": 1, "name": "S"}]
    assert result.data["epics"]["items"] == [{"id": 2, "name": "E"}]
