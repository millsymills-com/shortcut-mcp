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
async def test_list_iterations_shapes_rows(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/iterations").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "Sprint", "status": "started", "drop": 1}])
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_iterations", {})
    assert not result.is_error
    assert result.data["items"][0]["id"] == 1
    assert "drop" not in result.data["items"][0]
    assert result.data["truncated"] is False


@pytest.mark.asyncio
@respx.mock
async def test_get_iteration_returns_full_object(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/iterations/3").mock(return_value=httpx.Response(200, json={"id": 3}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_iteration", {"iteration_id": 3})
    assert not result.is_error
    assert result.data["id"] == 3


@pytest.mark.asyncio
@respx.mock
async def test_list_iteration_stories(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/iterations/3/stories").mock(
        return_value=httpx.Response(200, json=[{"id": 10, "name": "S", "description": "drop"}])
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_iteration_stories", {"iteration_id": 3})
    assert not result.is_error
    assert result.data["items"] == [{"id": 10, "name": "S"}]


# ---------------------------------------------------------------------------
# Write tool tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_create_iteration_posts_and_returns_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.post(f"{BASE}/iterations").mock(return_value=httpx.Response(201, json={"id": 1}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_create_iteration",
            {"name": "Sprint 1", "start_date": "2026-06-01", "end_date": "2026-06-14"},
        )
    assert not result.is_error
    assert result.data["id"] == 1
    body = json.loads(route.calls.last.request.content)
    assert body["name"] == "Sprint 1"
    assert body["start_date"] == "2026-06-01"
    assert body["end_date"] == "2026-06-14"
    assert "description" not in body


@pytest.mark.asyncio
@respx.mock
async def test_update_iteration_sends_partial_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.put(f"{BASE}/iterations/1").mock(return_value=httpx.Response(200, json={"id": 1}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_iteration", {"iteration_id": 1, "name": "X"})
    assert not result.is_error
    assert result.data["id"] == 1
    body = json.loads(route.calls.last.request.content)
    assert body == {"name": "X"}


@pytest.mark.asyncio
@respx.mock
async def test_update_iteration_tolerates_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.put(f"{BASE}/iterations/1").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_iteration", {"iteration_id": 1, "name": "X"})
    assert not result.is_error
    assert result.data == {"id": 1}


@pytest.mark.asyncio
@respx.mock
async def test_delete_iteration_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/iterations/2").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_iteration", {"iteration_id": 2})
    assert not result.is_error
    assert result.data == {"id": 2, "deleted": True}
    assert route.called
