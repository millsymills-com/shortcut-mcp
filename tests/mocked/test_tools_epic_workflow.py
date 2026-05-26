from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"


@pytest.mark.asyncio
@respx.mock
async def test_get_epic_workflow_returns_full_object(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/epic-workflow").mock(
        return_value=httpx.Response(200, json={"id": 1, "epic_states": [{"id": 5, "name": "To Do"}]})
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_epic_workflow", {})
    assert not result.is_error
    assert result.data["id"] == 1
