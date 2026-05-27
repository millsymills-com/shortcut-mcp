from __future__ import annotations

import json

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"
HEALTH = "health-9"


@pytest.mark.asyncio
@respx.mock
async def test_get_and_history_for_epic_and_objective(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/epics/1/health").mock(
        return_value=httpx.Response(200, json={"id": HEALTH, "status": "On Track"})
    )
    respx.get(f"{BASE}/epics/1/health-history").mock(
        return_value=httpx.Response(200, json=[{"id": HEALTH, "status": "On Track", "text": "ok", "drop": 1}])
    )
    respx.get(f"{BASE}/objectives/2/health").mock(
        return_value=httpx.Response(200, json={"id": "h2", "status": "At Risk"})
    )
    respx.get(f"{BASE}/objectives/2/health-history").mock(return_value=httpx.Response(200, json=[{"id": "h2"}]))
    server = create_server()
    async with Client(server) as client:
        eh = await client.call_tool("shortcut_get_epic_health", {"epic_id": 1})
        ehh = await client.call_tool("shortcut_list_epic_health_history", {"epic_id": 1})
        oh = await client.call_tool("shortcut_get_objective_health", {"objective_id": 2})
        ohh = await client.call_tool("shortcut_list_objective_health_history", {"objective_id": 2})
    assert eh.data["status"] == "On Track"
    assert ehh.data["items"][0] == {"id": HEALTH, "status": "On Track", "text": "ok"}
    assert oh.data["status"] == "At Risk"
    assert ohh.data["items"][0]["id"] == "h2"


@pytest.mark.asyncio
@respx.mock
async def test_create_epic_health_sends_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.post(f"{BASE}/epics/1/health").mock(return_value=httpx.Response(201, json={"id": HEALTH}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_create_epic_health", {"epic_id": 1, "status": "Off Track", "text": "blocked"}
        )
    assert not result.is_error
    assert json.loads(route.calls.last.request.content) == {"status": "Off Track", "text": "blocked"}


@pytest.mark.asyncio
@respx.mock
async def test_update_health_partial(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.put(f"{BASE}/health/{HEALTH}").mock(return_value=httpx.Response(200, json={"id": HEALTH}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_health", {"health_id": HEALTH, "status": "No Health"})
    assert not result.is_error
    assert json.loads(route.calls.last.request.content) == {"status": "No Health"}


@pytest.mark.asyncio
@respx.mock
async def test_create_health_rejects_invalid_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    post_route = respx.post(f"{BASE}/epics/1/health").mock(return_value=httpx.Response(201, json={"id": HEALTH}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_create_epic_health", {"epic_id": 1, "status": "Great"}, raise_on_error=False
        )
    assert result.is_error
    assert not post_route.called


@pytest.mark.asyncio
@respx.mock
async def test_update_health_no_fields_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    put_route = respx.put(f"{BASE}/health/{HEALTH}").mock(return_value=httpx.Response(200, json={"id": HEALTH}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_health", {"health_id": HEALTH}, raise_on_error=False)
    assert result.is_error
    assert not put_route.called


@pytest.mark.asyncio
@respx.mock
async def test_health_create_hidden_in_readonly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    server = create_server()
    async with Client(server) as client:
        names = {t.name for t in await client.list_tools()}
    assert "shortcut_create_epic_health" not in names
    assert "shortcut_get_epic_health" in names


@pytest.mark.asyncio
@respx.mock
async def test_create_objective_health_with_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.post(f"{BASE}/objectives/2/health").mock(return_value=httpx.Response(201, json={"id": "h2"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_create_objective_health", {"objective_id": 2, "status": "On Track", "text": "good"}
        )
    assert not result.is_error
    assert json.loads(route.calls.last.request.content) == {"status": "On Track", "text": "good"}


@pytest.mark.asyncio
@respx.mock
async def test_update_health_text_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.put(f"{BASE}/health/{HEALTH}").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_health", {"health_id": HEALTH, "text": "note"})
    assert result.data == {"id": HEALTH}
    assert json.loads(route.calls.last.request.content) == {"text": "note"}


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("text", ["", "   "])
async def test_update_health_rejects_empty_text(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    put_route = respx.put(f"{BASE}/health/{HEALTH}").mock(return_value=httpx.Response(200, json={"id": HEALTH}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_update_health", {"health_id": HEALTH, "text": text}, raise_on_error=False
        )
    assert result.is_error
    assert not put_route.called


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("text", ["", "   "])
async def test_create_epic_health_rejects_empty_text(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    post_route = respx.post(f"{BASE}/epics/1/health").mock(return_value=httpx.Response(201, json={"id": HEALTH}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_create_epic_health", {"epic_id": 1, "status": "On Track", "text": text}, raise_on_error=False
        )
    assert result.is_error
    assert "non-empty" in result.content[0].text
    assert not post_route.called


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("text", ["", "   "])
async def test_create_objective_health_rejects_empty_text(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    post_route = respx.post(f"{BASE}/objectives/2/health").mock(return_value=httpx.Response(201, json={"id": "h2"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_create_objective_health",
            {"objective_id": 2, "status": "On Track", "text": text},
            raise_on_error=False,
        )
    assert result.is_error
    assert "non-empty" in result.content[0].text
    assert not post_route.called
