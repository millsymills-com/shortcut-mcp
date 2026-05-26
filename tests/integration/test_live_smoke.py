"""Live smoke test — requires SHORTCUT_API_TOKEN in the environment.

Covers the real Shortcut workspace:
- ShortcutConfig loads and has a token
- GET /workflows returns a list with id + name
- GET /epics returns a list with id + name
- GET /stories/{id} returns the tracer-bullet story (id 60, or via search fallback)
- shortcut_list_epics MCP tool returns a shaped_list envelope
- shortcut_search_stories MCP tool returns a shaped_list envelope

Run with:
    SHORTCUT_API_TOKEN=<token> uv run pytest tests/integration/test_live_smoke.py -m live -v

Deselect from normal runs:
    uv run pytest -m "not live"
"""

from __future__ import annotations

import contextlib
import os

import pytest
from fastmcp import Client

from shortcut_mcp.clients.shortcut import ShortcutClient
from shortcut_mcp.config import ShortcutConfig
from shortcut_mcp.server import create_server


@pytest.mark.live
@pytest.mark.smoke
@pytest.mark.asyncio
async def test_live_read_surface(live_token: str) -> None:
    config = ShortcutConfig()
    assert config.shortcut_api_token is not None
    assert config.shortcut_api_token.get_secret_value() != ""

    async with ShortcutClient(token=live_token) as client:
        # -- workflows --
        workflows = await client.get("/workflows")
        assert isinstance(workflows, list), "expected a list from /workflows"
        assert len(workflows) > 0, "workspace has no workflows"
        first_wf = workflows[0]
        assert "id" in first_wf, "workflow missing 'id'"
        assert "name" in first_wf, "workflow missing 'name'"

        # -- epics --
        epics = await client.get("/epics")
        assert isinstance(epics, list), "expected a list from /epics"
        assert len(epics) > 0, "workspace has no epics"
        first_epic = epics[0]
        assert "id" in first_epic, "epic missing 'id'"
        assert "name" in first_epic, "epic missing 'name'"

        # -- tracer-bullet story --
        smoke_story_id: int | None = None

        env_id = os.environ.get("SHORTCUT_SMOKE_STORY_ID")
        if env_id:
            with contextlib.suppress(ValueError):
                smoke_story_id = int(env_id)

        if smoke_story_id is None:
            search = await client.get("/search/stories", params={"query": "label:tracer-bullet", "page_size": 5})
            hits = search.get("data", []) if isinstance(search, dict) else []
            if hits:
                smoke_story_id = int(hits[0]["id"])

        if smoke_story_id is None:
            pytest.skip("no SHORTCUT_SMOKE_STORY_ID and tracer-bullet search returned nothing — skipping get_story")

        story = await client.get(f"/stories/{smoke_story_id}")
        assert story["id"] == smoke_story_id, f"expected story id {smoke_story_id}, got {story['id']}"

    # -- MCP tool layer: shortcut_list_epics --
    # Verify the tool returns a shaped_list envelope; epics may legitimately be empty.
    server = create_server()
    async with Client(server) as mcp:
        result = await mcp.call_tool("shortcut_list_epics", {}, raise_on_error=False)
        assert not result.is_error, f"shortcut_list_epics returned an error: {result.data}"
        assert "items" in result.data, f"shortcut_list_epics missing 'items' key: {result.data}"
        assert "truncated" in result.data, f"shortcut_list_epics missing 'truncated' key: {result.data}"

        # -- MCP tool layer: shortcut_search_stories --
        # Broad query; search index may lag so we only check envelope shape, not count.
        result = await mcp.call_tool("shortcut_search_stories", {"query": "is:story", "limit": 5}, raise_on_error=False)
        assert not result.is_error, f"shortcut_search_stories returned an error: {result.data}"
        assert "items" in result.data, f"shortcut_search_stories missing 'items' key: {result.data}"
