from __future__ import annotations

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
