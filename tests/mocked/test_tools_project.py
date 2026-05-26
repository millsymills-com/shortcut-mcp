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
async def test_list_projects_shapes_rows(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/projects").mock(
        return_value=httpx.Response(200, json=[{"id": 2, "name": "P", "archived": False, "drop": 1}])
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_projects", {})
    assert not result.is_error
    assert result.data["items"][0] == {"id": 2, "name": "P", "archived": False}
    assert result.data["truncated"] is False


@pytest.mark.asyncio
@respx.mock
async def test_get_project_returns_full_object(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/projects/2").mock(return_value=httpx.Response(200, json={"id": 2}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_project", {"project_id": 2})
    assert not result.is_error
    assert result.data["id"] == 2


@pytest.mark.asyncio
@respx.mock
async def test_list_project_stories_shapes_rows(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/projects/2/stories").mock(
        return_value=httpx.Response(200, json=[{"id": 9, "name": "S", "drop": 1}])
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_project_stories", {"project_id": 2})
    assert not result.is_error
    assert result.data["items"] == [{"id": 9, "name": "S"}]


# ---------------------------------------------------------------------------
# Write tool tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_create_project_posts_and_returns_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.post(f"{BASE}/projects").mock(return_value=httpx.Response(201, json={"id": 2}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_create_project", {"name": "Backend"})
    assert not result.is_error
    assert result.data["id"] == 2
    body = json.loads(route.calls.last.request.content)
    assert body["name"] == "Backend"
    assert "team_id" not in body


@pytest.mark.asyncio
@respx.mock
async def test_update_project_tolerates_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.put(f"{BASE}/projects/2").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_project", {"project_id": 2, "archived": True})
    assert not result.is_error
    assert result.data == {"id": 2}


@pytest.mark.asyncio
@respx.mock
async def test_delete_project_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/projects/21").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_project", {"project_id": 21})
    assert not result.is_error
    assert result.data == {"id": 21, "deleted": True}
    assert route.called
