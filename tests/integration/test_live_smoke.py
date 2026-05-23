"""Live smoke test — requires SHORTCUT_API_TOKEN in the environment.

Covers the real Shortcut workspace:
- ShortcutConfig loads and has a token
- GET /workflows returns a list with id + name
- GET /epics returns a list with id + name
- GET /stories/{id} returns the tracer-bullet story (id 60, or via search fallback)

Run with:
    SHORTCUT_API_TOKEN=<token> uv run pytest tests/integration/test_live_smoke.py -m live -v

Deselect from normal runs:
    uv run pytest -m "not live"
"""

from __future__ import annotations

import os

import pytest

from shortcut_mcp.clients.shortcut import ShortcutClient
from shortcut_mcp.config import ShortcutConfig


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
            try:
                smoke_story_id = int(env_id)
            except ValueError:
                pass

        if smoke_story_id is None:
            search = await client.get("/search/stories", params={"query": "label:tracer-bullet", "page_size": 5})
            hits = search.get("data", []) if isinstance(search, dict) else []
            if hits:
                smoke_story_id = int(hits[0]["id"])

        if smoke_story_id is None:
            pytest.skip("no SHORTCUT_SMOKE_STORY_ID and tracer-bullet search returned nothing — skipping get_story")

        story = await client.get(f"/stories/{smoke_story_id}")
        assert story["id"] == smoke_story_id, f"expected story id {smoke_story_id}, got {story['id']}"
