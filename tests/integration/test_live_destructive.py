"""Opt-in live destructive test — disposable fixtures in an ISOLATED workspace.

Skips unless SHORTCUT_LIVE_WRITE_TESTS=true and SHORTCUT_TEST_WORKSPACE_TOKEN is
set (never the nightly read token). Creates its own story, deletes it via the
MCP tool, and asserts the resource is gone. Never runs on the default suite or
the nightly read cron.

Run with:
    SHORTCUT_LIVE_WRITE_TESTS=true SHORTCUT_TEST_WORKSPACE_TOKEN=<token> \\
        uv run pytest tests/integration/test_live_destructive.py -m live_write -v
"""

from __future__ import annotations

from contextlib import suppress

import pytest

from shortcut_mcp.clients.shortcut import ShortcutClient
from shortcut_mcp.errors import ShortcutClientError, ShortcutError


@pytest.mark.live_write
@pytest.mark.asyncio
async def test_live_delete_story_round_trip(live_write_token: str) -> None:
    async with ShortcutClient(token=live_write_token) as client:
        workflows = await client.get("/workflows")
        assert workflows, "isolated workspace has no workflows"
        state_id = workflows[0]["states"][0]["id"]

        created = await client.post(
            "/stories",
            json={"name": "shortcut-mcp live-destructive fixture (safe to delete)", "workflow_state_id": state_id},
        )
        story_id = created["id"]

        try:
            await client.delete(f"/stories/{story_id}")
        except ShortcutError:
            # Delete-under-test failed; best-effort cleanup of the fixture, then re-raise.
            with suppress(ShortcutError):
                await client.delete(f"/stories/{story_id}")
            raise

        with pytest.raises(ShortcutClientError):
            await client.get(f"/stories/{story_id}")
