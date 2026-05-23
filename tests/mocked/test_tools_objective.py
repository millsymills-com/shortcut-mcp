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
async def test_list_objectives_shapes_rows(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/objectives").mock(return_value=httpx.Response(200, json=[{"id": 9, "name": "Q3", "drop": 1}]))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_objectives", {})
    assert not result.is_error
    assert result.data["items"][0] == {"id": 9, "name": "Q3"}
    assert result.data["truncated"] is False


@pytest.mark.asyncio
@respx.mock
async def test_get_objective_returns_full_object(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/objectives/9").mock(return_value=httpx.Response(200, json={"id": 9}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_objective", {"objective_id": 9})
    assert not result.is_error
    assert result.data["id"] == 9


@pytest.mark.asyncio
@respx.mock
async def test_list_objective_epics(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/objectives/9/epics").mock(
        return_value=httpx.Response(200, json=[{"id": 20, "name": "E", "description": "drop"}])
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_objective_epics", {"objective_id": 9})
    assert not result.is_error
    assert result.data["items"] == [{"id": 20, "name": "E"}]


# ---------------------------------------------------------------------------
# Write tool tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_create_objective_posts_and_returns_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.post(f"{BASE}/objectives").mock(return_value=httpx.Response(200, json={"id": 2}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_create_objective", {"name": "Q3 Goals"})
    assert not result.is_error
    assert result.data["id"] == 2
    body = json.loads(route.calls.last.request.content)
    assert body["name"] == "Q3 Goals"
    assert "description" not in body
    assert "state" not in body


@pytest.mark.asyncio
@respx.mock
async def test_update_objective_tolerates_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.put(f"{BASE}/objectives/2").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_objective", {"objective_id": 2, "name": "Updated"})
    assert not result.is_error
    assert result.data == {"id": 2}
