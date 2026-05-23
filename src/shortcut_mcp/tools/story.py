"""Story tools. v0.1: shortcut_get_story (the tracer bullet)."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import get_client, read_tags, shaped_list


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_get_story",
        description="Fetch a Shortcut story by its numeric ID.",
        tags=read_tags("story"),
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )
    async def shortcut_get_story(ctx: Context, story_id: int) -> dict[str, Any]:
        return await get_client(ctx).get(f"/stories/{_seg(str(story_id))}")

    @server.tool(
        name="shortcut_list_story_history",
        description="List the change history for a story (most recent first).",
        tags=read_tags("story"),
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )
    async def shortcut_list_story_history(
        ctx: Context, story_id: int, limit: int = 50
    ) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/stories/{_seg(str(story_id))}/history")
        return shaped_list(rows, lambda r: r, limit=limit)
