from __future__ import annotations

import json

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"
ET = "tmpl-abc"


@pytest.mark.asyncio
@respx.mock
async def test_list_and_get_entity_templates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/entity-templates").mock(
        return_value=httpx.Response(
            200, json=[{"id": ET, "name": "Bug", "author_id": "a", "entity_type": "story-template"}]
        )
    )
    respx.get(f"{BASE}/entity-templates/{ET}").mock(return_value=httpx.Response(200, json={"id": ET, "name": "Bug"}))
    server = create_server()
    async with Client(server) as client:
        listed = await client.call_tool("shortcut_list_entity_templates", {})
        got = await client.call_tool("shortcut_get_entity_template", {"entity_template_id": ET})
    assert listed.data["items"][0]["id"] == ET
    assert got.data["id"] == ET


@pytest.mark.asyncio
@respx.mock
async def test_create_entity_template_passes_story_contents(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.post(f"{BASE}/entity-templates").mock(return_value=httpx.Response(201, json={"id": ET}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_create_entity_template",
            {"name": "Bug", "story_contents": {"story_type": "bug", "name": "T"}},
        )
    assert not result.is_error
    assert json.loads(route.calls.last.request.content) == {
        "name": "Bug",
        "story_contents": {"story_type": "bug", "name": "T"},
    }


@pytest.mark.asyncio
@respx.mock
async def test_update_entity_template_partial(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.put(f"{BASE}/entity-templates/{ET}").mock(return_value=httpx.Response(200, json={"id": ET}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_entity_template", {"entity_template_id": ET, "name": "New"})
    assert not result.is_error
    assert json.loads(route.calls.last.request.content) == {"name": "New"}


@pytest.mark.asyncio
@respx.mock
async def test_delete_entity_template(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.delete(f"{BASE}/entity-templates/{ET}").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_entity_template", {"entity_template_id": ET})
    assert result.data == {"id": ET, "deleted": True}


@pytest.mark.asyncio
@respx.mock
async def test_create_entity_template_includes_author_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.post(f"{BASE}/entity-templates").mock(return_value=httpx.Response(201, json={"id": ET}))
    server = create_server()
    async with Client(server) as client:
        await client.call_tool(
            "shortcut_create_entity_template",
            {"name": "Bug", "story_contents": {"name": "T"}, "author_id": "uuid-1"},
        )
    assert json.loads(route.calls.last.request.content) == {
        "name": "Bug",
        "story_contents": {"name": "T"},
        "author_id": "uuid-1",
    }


@pytest.mark.asyncio
@respx.mock
async def test_update_entity_template_story_contents(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.put(f"{BASE}/entity-templates/{ET}").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_update_entity_template",
            {"entity_template_id": ET, "story_contents": {"story_type": "chore"}},
        )
    assert result.data == {"id": ET}
    assert json.loads(route.calls.last.request.content) == {"story_contents": {"story_type": "chore"}}
