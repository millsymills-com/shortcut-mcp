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
async def test_list_categories_shapes_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/categories").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "Q1", "color": "#fff", "type": "milestone", "x": 1}])
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_categories", {})
    assert not result.is_error
    assert result.data["items"][0] == {"id": 1, "name": "Q1", "color": "#fff", "type": "milestone"}


@pytest.mark.asyncio
@respx.mock
async def test_get_category_and_association_lists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/categories/7").mock(return_value=httpx.Response(200, json={"id": 7, "name": "Q1"}))
    respx.get(f"{BASE}/categories/7/milestones").mock(return_value=httpx.Response(200, json=[{"id": 3, "name": "M"}]))
    respx.get(f"{BASE}/categories/7/objectives").mock(return_value=httpx.Response(200, json=[{"id": 4, "name": "O"}]))
    server = create_server()
    async with Client(server) as client:
        got = await client.call_tool("shortcut_get_category", {"category_id": 7})
        ms = await client.call_tool("shortcut_list_category_milestones", {"category_id": 7})
        objs = await client.call_tool("shortcut_list_category_objectives", {"category_id": 7})
    assert got.data["id"] == 7
    assert ms.data["items"][0]["id"] == 3
    assert objs.data["items"][0]["id"] == 4


@pytest.mark.asyncio
@respx.mock
async def test_create_category_sends_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.post(f"{BASE}/categories").mock(return_value=httpx.Response(201, json={"id": 9, "name": "Q2"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_create_category", {"name": "Q2", "color": "#abc"})
    assert not result.is_error
    assert json.loads(route.calls.last.request.content) == {"name": "Q2", "color": "#abc"}


@pytest.mark.asyncio
@respx.mock
async def test_update_category_sends_partial_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.put(f"{BASE}/categories/9").mock(return_value=httpx.Response(200, json={"id": 9}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_category", {"category_id": 9, "archived": True})
    assert not result.is_error
    assert json.loads(route.calls.last.request.content) == {"archived": True}


@pytest.mark.asyncio
@respx.mock
async def test_delete_category_returns_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.delete(f"{BASE}/categories/9").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_category", {"category_id": 9})
    assert result.data == {"id": 9, "deleted": True}


@pytest.mark.asyncio
@respx.mock
async def test_category_write_hidden_in_readonly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    server = create_server()
    async with Client(server) as client:
        names = {t.name for t in await client.list_tools()}
    assert "shortcut_create_category" not in names
    assert "shortcut_list_categories" in names


@pytest.mark.asyncio
@respx.mock
async def test_create_category_includes_external_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.post(f"{BASE}/categories").mock(return_value=httpx.Response(201, json={"id": 9}))
    server = create_server()
    async with Client(server) as client:
        await client.call_tool("shortcut_create_category", {"name": "Q2", "external_id": "ext-1"})
    assert json.loads(route.calls.last.request.content) == {"name": "Q2", "external_id": "ext-1"}


@pytest.mark.asyncio
@respx.mock
async def test_update_category_name_and_color(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.put(f"{BASE}/categories/9").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_category", {"category_id": 9, "name": "N", "color": "#1"})
    assert result.data == {"id": 9}
    assert json.loads(route.calls.last.request.content) == {"name": "N", "color": "#1"}


@pytest.mark.asyncio
@respx.mock
async def test_delete_category_runtime_guard_blocks_without_destructive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/categories/9").mock(return_value=httpx.Response(204))
    server = create_server()
    # Re-enable the tag the visibility gate stripped, so the call reaches the
    # in-body require_destructive() guard instead of failing at "unknown tool".
    server.enable(tags={"destructive"})
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_category", {"category_id": 9}, raise_on_error=False)
    assert result.is_error
    assert "mode_denied" in result.content[0].text
    assert not route.called


@pytest.mark.asyncio
@respx.mock
async def test_update_category_no_fields_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    put_route = respx.put(f"{BASE}/categories/9").mock(return_value=httpx.Response(200, json={"id": 9}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_category", {"category_id": 9}, raise_on_error=False)
    assert result.is_error
    assert not put_route.called


@pytest.mark.asyncio
@respx.mock
async def test_get_category_propagates_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/categories/404").mock(return_value=httpx.Response(404, json={"message": "Not Found"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_category", {"category_id": 404}, raise_on_error=False)
    assert result.is_error
    assert "404" in result.content[0].text
