from __future__ import annotations

import json

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"
KR = "kr-123"


@pytest.mark.asyncio
@respx.mock
async def test_get_key_result_returns_full_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/key-results/{KR}").mock(return_value=httpx.Response(200, json={"id": KR, "name": "KR"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_key_result", {"key_result_id": KR})
    assert not result.is_error
    assert result.data["id"] == KR


@pytest.mark.asyncio
@respx.mock
async def test_update_key_result_sends_partial_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.put(f"{BASE}/key-results/{KR}").mock(return_value=httpx.Response(200, json={"id": KR}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_update_key_result",
            {"key_result_id": KR, "observed_value": {"numeric_value": "5.00"}},
        )
    assert not result.is_error
    assert result.data["id"] == KR
    body = json.loads(route.calls.last.request.content)
    assert body == {"observed_value": {"numeric_value": "5.00"}}


@pytest.mark.asyncio
@respx.mock
async def test_update_key_result_sends_all_value_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.put(f"{BASE}/key-results/{KR}").mock(return_value=httpx.Response(200, json={"id": KR}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_update_key_result",
            {
                "key_result_id": KR,
                "name": "renamed",
                "initial_observed_value": {"numeric_value": "0.00"},
                "target_value": {"boolean_value": True},
            },
        )
    assert not result.is_error
    body = json.loads(route.calls.last.request.content)
    assert body == {
        "name": "renamed",
        "initial_observed_value": {"numeric_value": "0.00"},
        "target_value": {"boolean_value": True},
    }


@pytest.mark.asyncio
@respx.mock
async def test_update_key_result_tolerates_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.put(f"{BASE}/key-results/{KR}").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_key_result", {"key_result_id": KR, "name": "renamed"})
    assert not result.is_error
    assert result.data == {"id": KR}


@pytest.mark.asyncio
@respx.mock
async def test_update_key_result_no_fields_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    put_route = respx.put(f"{BASE}/key-results/{KR}").mock(return_value=httpx.Response(200, json={"id": KR}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_key_result", {"key_result_id": KR}, raise_on_error=False)
    assert result.is_error
    assert not put_route.called


@pytest.mark.asyncio
@respx.mock
async def test_update_key_result_hidden_in_readonly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    server = create_server()
    async with Client(server) as client:
        names = {t.name for t in await client.list_tools()}
    assert "shortcut_update_key_result" not in names
    assert "shortcut_get_key_result" in names
