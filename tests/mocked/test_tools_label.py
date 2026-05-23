from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"


@pytest.mark.asyncio
@respx.mock
async def test_list_labels_shapes_rows(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/labels").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "bug", "color": "red", "drop": 1}])
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_labels", {})
    assert not result.is_error
    assert result.data["items"][0] == {"id": 1, "name": "bug", "color": "red"}
    assert result.data["truncated"] is False


@pytest.mark.asyncio
@respx.mock
async def test_get_label_returns_full_object(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/labels/1").mock(return_value=httpx.Response(200, json={"id": 1}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_label", {"label_id": 1})
    assert not result.is_error
    assert result.data["id"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_list_label_stories_shapes_rows(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/labels/1/stories").mock(
        return_value=httpx.Response(200, json=[{"id": 7, "name": "S", "drop": 1}])
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_label_stories", {"label_id": 1})
    assert not result.is_error
    assert result.data["items"] == [{"id": 7, "name": "S"}]


@pytest.mark.asyncio
@respx.mock
async def test_list_label_epics_shapes_rows(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/labels/1/epics").mock(return_value=httpx.Response(200, json=[{"id": 8, "name": "E", "drop": 1}]))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_label_epics", {"label_id": 1})
    assert not result.is_error
    assert result.data["items"] == [{"id": 8, "name": "E"}]
