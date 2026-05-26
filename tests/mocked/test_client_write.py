"""Tests for ShortcutClient write extensions: multipart upload and DELETE with body."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
import respx

if TYPE_CHECKING:
    from pathlib import Path

from shortcut_mcp.clients.shortcut import ShortcutClient
from shortcut_mcp.errors import ShortcutError


@pytest.mark.asyncio
@respx.mock
async def test_upload_sends_multipart(tmp_path: Path) -> None:
    f = tmp_path / "a.txt"
    f.write_bytes(b"hello")
    route = respx.post("https://api.app.shortcut.com/api/v3/files").mock(
        return_value=httpx.Response(201, json=[{"id": 9, "name": "a.txt"}])
    )
    async with ShortcutClient(token="x") as c:
        out = await c.upload("/files", file_path=str(f))
    req = route.calls.last.request
    content_type = req.headers["content-type"]
    assert content_type.startswith("multipart/form-data")
    # the boundary advertised in the header must match the delimiter used in the body
    boundary = content_type.split("boundary=", 1)[1]
    assert f"--{boundary}".encode() in req.content
    assert b"hello" in req.content
    assert out == [{"id": 9, "name": "a.txt"}]


@pytest.mark.asyncio
async def test_upload_rejects_missing_file() -> None:
    async with ShortcutClient(token="x") as c:
        with pytest.raises(ShortcutError):
            await c.upload("/files", file_path="/nonexistent/zzz.bin")


@pytest.mark.asyncio
async def test_upload_rejects_oversized(tmp_path: Path) -> None:
    f = tmp_path / "big.bin"
    f.write_bytes(b"x" * 1024)
    async with ShortcutClient(token="x") as c:
        with pytest.raises(ShortcutError):
            await c.upload("/files", file_path=str(f), max_bytes=10)


@pytest.mark.asyncio
@respx.mock
async def test_delete_sends_json_body() -> None:
    import json as _json

    route = respx.delete("https://api.app.shortcut.com/api/v3/stories/1/comments/2/reactions").mock(
        return_value=httpx.Response(200, json={"deleted": True})
    )
    async with ShortcutClient(token="x") as c:
        await c.delete("/stories/1/comments/2/reactions", json={"emoji": "x"})
    assert _json.loads(route.calls.last.request.content) == {"emoji": "x"}
