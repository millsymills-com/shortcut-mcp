from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"


@pytest.mark.asyncio
@respx.mock
async def test_list_external_link_stories_shapes_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.get(f"{BASE}/external-link/stories").mock(
        return_value=httpx.Response(200, json=[{"id": 7, "name": "S", "drop": 1}])
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_list_external_link_stories", {"external_link": "https://example.com/x"}
        )
    assert not result.is_error
    assert result.data["items"] == [{"id": 7, "name": "S"}]
    assert route.calls.last.request.url.params["external_link"] == "https://example.com/x"


@pytest.mark.asyncio
@respx.mock
async def test_list_external_link_stories_rejects_non_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.get(f"{BASE}/external-link/stories").mock(return_value=httpx.Response(200, json=[]))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_list_external_link_stories", {"external_link": "not-a-url"}, raise_on_error=False
        )
    assert result.is_error
    assert not route.called
