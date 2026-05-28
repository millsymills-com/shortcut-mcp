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
    assert "https?://" in result.content[0].text
    assert not route.called


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    "bad",
    [
        "ftp://host/x",  # non-http(s) scheme
        "https://" + "a" * 2048,  # exceeds max_length=2048
        "https://example.com/x\n",  # trailing newline
    ],
)
async def test_list_external_link_stories_rejects_malformed_url(monkeypatch: pytest.MonkeyPatch, bad: str) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.get(f"{BASE}/external-link/stories").mock(return_value=httpx.Response(200, json=[]))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_list_external_link_stories", {"external_link": bad}, raise_on_error=False
        )
    assert result.is_error
    assert not route.called


@pytest.mark.asyncio
@respx.mock
async def test_list_external_link_stories_preserves_query_and_fragment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    url = "https://example.com/a?b=1&c=2#frag"
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.get(f"{BASE}/external-link/stories").mock(return_value=httpx.Response(200, json=[]))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_external_link_stories", {"external_link": url})
    assert not result.is_error
    assert route.calls.last.request.url.params["external_link"] == url
