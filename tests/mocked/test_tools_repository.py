from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"


@pytest.mark.asyncio
@respx.mock
async def test_list_repositories_shapes_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/repositories").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": 1, "name": "api", "full_name": "org/api", "type": "github", "url": "u", "drop": 1}],
        )
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_repositories", {})
    assert not result.is_error
    assert result.data["items"][0] == {"id": 1, "name": "api", "full_name": "org/api", "type": "github", "url": "u"}
    assert result.data["truncated"] is False


@pytest.mark.asyncio
@respx.mock
async def test_list_repositories_truncates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/repositories").mock(return_value=httpx.Response(200, json=[{"id": 1}, {"id": 2}, {"id": 3}]))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_repositories", {"limit": 2})
    assert not result.is_error
    assert len(result.data["items"]) == 2
    assert result.data["truncated"] is True


@pytest.mark.asyncio
@respx.mock
async def test_get_repository_returns_full_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/repositories/7").mock(return_value=httpx.Response(200, json={"id": 7, "name": "api"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_repository", {"repo_id": 7})
    assert not result.is_error
    assert result.data["id"] == 7
