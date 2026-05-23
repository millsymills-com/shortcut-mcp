from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"


@pytest.mark.asyncio
@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(rows=st.lists(st.fixed_dictionaries({"id": st.integers(), "name": st.text()}), max_size=40))
async def test_search_stories_always_returns_items_envelope(monkeypatch, rows):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    with respx.mock:
        respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
        respx.get(f"{BASE}/search/stories").mock(
            return_value=httpx.Response(200, json={"data": rows, "next": None, "total": len(rows)})
        )
        server = create_server()
        async with Client(server) as client:
            result = await client.call_tool("shortcut_search_stories", {"query": "q", "limit": 25})
    assert set(result.data) >= {"items", "truncated"}
    assert len(result.data["items"]) <= 25
