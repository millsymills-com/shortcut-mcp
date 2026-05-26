from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"


@pytest.mark.asyncio
@respx.mock
async def test_get_story_link_returns_full_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/story-links/4").mock(return_value=httpx.Response(200, json={"id": 4, "verb": "blocks"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_story_link", {"story_link_id": 4})
    assert not result.is_error
    assert result.data["id"] == 4
