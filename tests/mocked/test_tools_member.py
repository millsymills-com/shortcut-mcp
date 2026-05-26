from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"

RAW_MEMBER = {
    "id": "m1",
    "disabled": False,
    "profile": {"name": "Ada", "mention_name": "ada", "email_address": "a@b.c"},
}


@pytest.mark.asyncio
@respx.mock
async def test_list_members_flattens_profile(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/members").mock(return_value=httpx.Response(200, json=[RAW_MEMBER]))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_members", {})
    assert not result.is_error
    assert result.data["items"][0] == {
        "id": "m1",
        "disabled": False,
        "name": "Ada",
        "mention_name": "ada",
        "email_address": "a@b.c",
    }
    assert result.data["truncated"] is False


@pytest.mark.asyncio
@respx.mock
async def test_get_member_returns_full_object(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/members/m1").mock(return_value=httpx.Response(200, json={"id": "m1"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_member", {"member_id": "m1"})
    assert not result.is_error
    assert result.data["id"] == "m1"


@pytest.mark.asyncio
@respx.mock
async def test_get_current_member_returns_full_object(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "me"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_current_member", {})
    assert not result.is_error
    assert result.data["id"] == "me"
