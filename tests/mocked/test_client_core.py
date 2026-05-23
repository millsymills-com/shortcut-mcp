"""Tests for the ShortcutClient core: URL validation, path encoding, GET happy path."""

from __future__ import annotations

import httpx
import pytest
import respx

from shortcut_mcp.clients.shortcut import ShortcutClient, _seg


def test_seg_percent_encodes_unsafe_characters() -> None:
    assert _seg("hello world") == "hello%20world"
    assert _seg("a/b") == "a%2Fb"
    assert _seg("café") == "caf%C3%A9"


def test_seg_passes_safe_characters() -> None:
    assert _seg("abc-DEF_123.tilde~") == "abc-DEF_123.tilde~"


@pytest.mark.asyncio
@respx.mock
async def test_rejects_absolute_url() -> None:
    async with ShortcutClient(token="x", base_url="https://api.app.shortcut.com/api/v3") as client:
        with pytest.raises(ValueError, match="absolute"):
            await client.get("https://evil.example.com/stories")


@pytest.mark.asyncio
@respx.mock
async def test_rejects_path_without_leading_slash() -> None:
    async with ShortcutClient(token="x", base_url="https://api.app.shortcut.com/api/v3") as client:
        with pytest.raises(ValueError, match="leading slash"):
            await client.get("stories/1")


@pytest.mark.asyncio
@respx.mock
async def test_get_sends_token_header_and_returns_json() -> None:
    route = respx.get("https://api.app.shortcut.com/api/v3/stories/123").mock(
        return_value=httpx.Response(200, json={"id": 123, "name": "Test"})
    )
    async with ShortcutClient(token="abc-token") as client:
        result = await client.get("/stories/123")
    assert result == {"id": 123, "name": "Test"}
    assert route.calls.last.request.headers["Shortcut-Token"] == "abc-token"


@pytest.mark.asyncio
@respx.mock
async def test_get_with_params_passes_query_string() -> None:
    route = respx.get("https://api.app.shortcut.com/api/v3/search/stories").mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    async with ShortcutClient(token="x") as client:
        await client.get("/search/stories", params={"query": "label:tracer-bullet"})
    assert route.calls.last.request.url.params["query"] == "label:tracer-bullet"


@pytest.mark.asyncio
@respx.mock
async def test_204_returns_none() -> None:
    respx.put("https://api.app.shortcut.com/api/v3/stories/1").mock(return_value=httpx.Response(204))
    async with ShortcutClient(token="x") as client:
        result = await client.put("/stories/1", json={})
    assert result is None
