from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"


@pytest.mark.asyncio
@respx.mock
async def test_get_story_task_returns_full_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/stories/5/tasks/9").mock(return_value=httpx.Response(200, json={"id": 9, "complete": False}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_story_task", {"story_id": 5, "task_id": 9})
    assert not result.is_error
    assert result.data["id"] == 9
