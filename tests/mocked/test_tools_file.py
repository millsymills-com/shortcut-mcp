from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from pathlib import Path
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"


@pytest.mark.asyncio
@respx.mock
async def test_list_files_shapes_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/files").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": 1, "name": "a.png", "content_type": "image/png", "drop": 1}],
        )
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_files", {})
    assert not result.is_error
    assert result.data["items"][0] == {"id": 1, "name": "a.png", "content_type": "image/png"}
    assert result.data["truncated"] is False


@pytest.mark.asyncio
@respx.mock
async def test_get_file_returns_full_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/files/1").mock(return_value=httpx.Response(200, json={"id": 1}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_file", {"file_id": 1})
    assert not result.is_error
    assert result.data["id"] == 1


# ---------------------------------------------------------------------------
# Write tool tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_upload_file_sends_multipart(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    f = tmp_path / "f.txt"
    f.write_bytes(b"hello upload")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.post(f"{BASE}/files").mock(return_value=httpx.Response(201, json=[{"id": 7, "name": "f.txt"}]))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_upload_file", {"path": str(f)})
    assert not result.is_error
    # upload returns a list; FastMCP serialises it as a text content block
    returned = json.loads(result.content[0].text)
    assert returned[0]["id"] == 7
    content_type = route.calls.last.request.headers["content-type"]
    assert content_type.startswith("multipart/form-data")


@pytest.mark.asyncio
@respx.mock
async def test_update_file_sends_partial_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.put(f"{BASE}/files/7").mock(return_value=httpx.Response(200, json={"id": 7}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_file", {"file_id": 7, "name": "r.txt"})
    assert not result.is_error
    assert result.data["id"] == 7
    body = json.loads(route.calls.last.request.content)
    assert body == {"name": "r.txt"}


@pytest.mark.asyncio
@respx.mock
async def test_delete_file_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/files/30").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_file", {"file_id": 30})
    assert not result.is_error
    assert result.data == {"id": 30, "deleted": True}
    assert route.called
