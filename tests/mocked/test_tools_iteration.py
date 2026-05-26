from __future__ import annotations

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
