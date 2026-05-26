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
async def test_search_iterations_routes_to_endpoint(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/search/iterations").mock(
        return_value=httpx.Response(
            200,
            json={"data": [{"id": 7, "name": "Sprint", "status": "started", "drop": 1}], "next": None, "total": 1},
        )
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_search_iterations", {"query": "x"})
    assert not result.is_error
    assert result.data["items"] == [{"id": 7, "name": "Sprint", "status": "started"}]


@pytest.mark.asyncio
@respx.mock
async def test_search_objectives_routes_to_endpoint(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/search/objectives").mock(
        return_value=httpx.Response(
            200,
            json={"data": [{"id": 8, "name": "Q3", "state": "active", "drop": 1}], "next": None, "total": 1},
        )
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_search_objectives", {"query": "x"})
    assert not result.is_error
    assert result.data["items"] == [{"id": 8, "name": "Q3", "state": "active"}]


@pytest.mark.asyncio
@respx.mock
async def test_query_stories_raises_on_empty_body(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.post(f"{BASE}/stories/search").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_query_stories", {}, raise_on_error=False)
    assert result.is_error


@pytest.mark.asyncio
@respx.mock
async def test_query_stories_sends_filter_body(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.post(f"{BASE}/stories/search").mock(return_value=httpx.Response(200, json=[]))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_query_stories", {"archived": False, "epic_id": 7}, raise_on_error=False
        )
    assert not result.is_error
    body = json.loads(route.calls.last.request.content)
    assert body == {"archived": False, "epic_id": 7}


@pytest.mark.asyncio
@respx.mock
async def test_search_stories_truncates_at_limit(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    rows = [{"id": i, "name": f"S{i}"} for i in range(5)]
    respx.get(f"{BASE}/search/stories").mock(
        return_value=httpx.Response(200, json={"data": rows, "next": None, "total": 5})
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_search_stories", {"query": "x", "limit": 2})
    assert not result.is_error
    assert result.data["truncated"] is True
    assert len(result.data["items"]) == 2
    assert result.data["total"] == 5


@pytest.mark.asyncio
@respx.mock
async def test_search_stories_rejects_limit_below_one(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.get(f"{BASE}/search/stories").mock(return_value=httpx.Response(200, json={"data": []}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_search_stories", {"query": "x", "limit": 0}, raise_on_error=False)
    assert result.is_error
    assert not route.called  # validation rejects before any HTTP call


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


@pytest.mark.asyncio
@respx.mock
async def test_global_search_reports_truncation_when_total_exceeds_page(monkeypatch):
    """limit>25 caps the page at 25 rows; total must drive truncated=True (issue #14)."""
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    page = [{"id": i, "name": f"S{i}"} for i in range(25)]
    respx.get(f"{BASE}/search").mock(
        return_value=httpx.Response(
            200,
            json={"stories": {"data": page, "total": 100}, "epics": {"data": [], "total": 0}},
        )
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_search", {"query": "x", "limit": 50})
    assert not result.is_error
    assert result.data["stories"]["truncated"] is True
    assert result.data["stories"]["total"] == 100
    assert len(result.data["stories"]["items"]) == 25
    assert result.data["epics"]["truncated"] is False
