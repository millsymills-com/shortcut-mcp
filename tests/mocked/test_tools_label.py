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


# ---------------------------------------------------------------------------
# Write tool tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_create_label_posts_and_returns_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.post(f"{BASE}/labels").mock(return_value=httpx.Response(201, json={"id": 1, "name": "bug"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_create_label", {"name": "bug"})
    assert not result.is_error
    assert result.data["id"] == 1
    body = json.loads(route.calls.last.request.content)
    assert body["name"] == "bug"
    assert "color" not in body
    assert "description" not in body


@pytest.mark.asyncio
@respx.mock
async def test_update_label_sends_partial_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.put(f"{BASE}/labels/1").mock(return_value=httpx.Response(200, json={"id": 1}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_label", {"label_id": 1, "archived": True})
    assert not result.is_error
    assert result.data["id"] == 1
    body = json.loads(route.calls.last.request.content)
    assert body == {"archived": True}


@pytest.mark.asyncio
@respx.mock
async def test_update_label_tolerates_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.put(f"{BASE}/labels/1").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_label", {"label_id": 1, "archived": True})
    assert not result.is_error
    assert result.data == {"id": 1}


@pytest.mark.asyncio
@respx.mock
async def test_delete_label_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/labels/15").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_label", {"label_id": 15})
    assert not result.is_error
    assert result.data == {"id": 15, "deleted": True}
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_delete_label_surfaces_client_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.delete(f"{BASE}/labels/15").mock(return_value=httpx.Response(404, json={"message": "Not Found"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_label", {"label_id": 15}, raise_on_error=False)
    assert result.is_error
    assert "404" in result.content[0].text


@pytest.mark.asyncio
@respx.mock
async def test_update_label_with_no_fields_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    put_route = respx.put(f"{BASE}/labels/1").mock(return_value=httpx.Response(200, json={"id": 1}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_label", {"label_id": 1}, raise_on_error=False)
    assert result.is_error
    assert "at least one field" in result.content[0].text
    assert not put_route.called
