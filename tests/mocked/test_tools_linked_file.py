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
async def test_list_linked_files_shapes_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/linked-files").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": 2, "name": "doc", "type": "google", "drop": 1}],
        )
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_linked_files", {})
    assert not result.is_error
    assert result.data["items"][0] == {"id": 2, "name": "doc", "type": "google"}
    assert result.data["truncated"] is False


@pytest.mark.asyncio
@respx.mock
async def test_get_linked_file_returns_full_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/linked-files/2").mock(return_value=httpx.Response(200, json={"id": 2}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_linked_file", {"linked_file_id": 2})
    assert not result.is_error
    assert result.data["id"] == 2


# ---------------------------------------------------------------------------
# Write tool tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_create_linked_file_posts_and_returns_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.post(f"{BASE}/linked-files").mock(return_value=httpx.Response(201, json={"id": 3}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_create_linked_file",
            {"name": "Design doc", "url": "https://example.com/doc", "type": "google"},
        )
    assert not result.is_error
    assert result.data["id"] == 3
    body = json.loads(route.calls.last.request.content)
    assert body["name"] == "Design doc"
    assert body["url"] == "https://example.com/doc"
    assert body["type"] == "google"
    assert "description" not in body


@pytest.mark.asyncio
@respx.mock
async def test_update_linked_file_sends_partial_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.put(f"{BASE}/linked-files/3").mock(return_value=httpx.Response(200, json={"id": 3}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_linked_file", {"linked_file_id": 3, "name": "x"})
    assert not result.is_error
    assert result.data["id"] == 3
    body = json.loads(route.calls.last.request.content)
    assert body == {"name": "x"}


@pytest.mark.asyncio
@respx.mock
async def test_delete_linked_file_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/linked-files/41").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_linked_file", {"linked_file_id": 41})
    assert not result.is_error
    assert result.data == {"id": 41, "deleted": True}
    assert route.called
