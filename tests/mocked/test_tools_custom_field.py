from __future__ import annotations

import json

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"
CF = "12345678-1234-1234-1234-123456789abc"


@pytest.mark.asyncio
@respx.mock
async def test_list_custom_fields_shapes_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/custom-fields").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": CF, "name": "Priority", "field_type": "enum", "enabled": True, "position": 1, "drop": 9}],
        )
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_custom_fields", {})
    assert not result.is_error
    assert result.data["items"][0] == {
        "id": CF,
        "name": "Priority",
        "field_type": "enum",
        "enabled": True,
        "position": 1,
    }


@pytest.mark.asyncio
@respx.mock
async def test_get_custom_field_returns_full_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/custom-fields/{CF}").mock(return_value=httpx.Response(200, json={"id": CF, "name": "Priority"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_custom_field", {"custom_field_id": CF})
    assert not result.is_error
    assert result.data["id"] == CF


@pytest.mark.asyncio
@respx.mock
async def test_update_custom_field_sends_partial_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.put(f"{BASE}/custom-fields/{CF}").mock(return_value=httpx.Response(200, json={"id": CF}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_update_custom_field", {"custom_field_id": CF, "enabled": False, "name": "P"}
        )
    assert not result.is_error
    assert json.loads(route.calls.last.request.content) == {"enabled": False, "name": "P"}


@pytest.mark.asyncio
@respx.mock
async def test_update_custom_field_no_fields_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    put_route = respx.put(f"{BASE}/custom-fields/{CF}").mock(return_value=httpx.Response(200, json={"id": CF}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_custom_field", {"custom_field_id": CF}, raise_on_error=False)
    assert result.is_error
    assert not put_route.called


@pytest.mark.asyncio
@respx.mock
async def test_delete_custom_field_requires_destructive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.delete(f"{BASE}/custom-fields/{CF}").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_custom_field", {"custom_field_id": CF})
    assert not result.is_error
    assert result.data == {"id": CF, "deleted": True}


@pytest.mark.asyncio
@respx.mock
async def test_custom_field_write_hidden_in_readonly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    server = create_server()
    async with Client(server) as client:
        names = {t.name for t in await client.list_tools()}
    assert "shortcut_update_custom_field" not in names
    assert "shortcut_delete_custom_field" not in names
    assert "shortcut_list_custom_fields" in names


@pytest.mark.asyncio
@respx.mock
async def test_update_custom_field_description_and_icon(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.put(f"{BASE}/custom-fields/{CF}").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_update_custom_field",
            {"custom_field_id": CF, "description": "d", "icon_set_identifier": "icon"},
        )
    assert result.data == {"id": CF}
    assert json.loads(route.calls.last.request.content) == {"description": "d", "icon_set_identifier": "icon"}


@pytest.mark.asyncio
@respx.mock
async def test_delete_custom_field_runtime_guard_blocks_without_destructive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/custom-fields/{CF}").mock(return_value=httpx.Response(204))
    server = create_server()
    # Re-enable the tag the visibility gate stripped, so the call reaches the
    # in-body require_destructive() guard instead of failing at "unknown tool".
    server.enable(tags={"destructive"})
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_custom_field", {"custom_field_id": CF}, raise_on_error=False)
    assert result.is_error
    assert "mode_denied" in result.content[0].text
    assert not route.called
