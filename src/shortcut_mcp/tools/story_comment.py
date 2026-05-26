"""Story comment read tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import get_client, read_tags, shape_comment_summary, shaped_list

_MODULE = "story_comment"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_story_comments",
        description="List comments on a story (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_story_comments(ctx: Context, story_id: int, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/stories/{_seg(str(story_id))}/comments")
        return shaped_list(rows, shape_comment_summary, limit=limit)

    @server.tool(
        name="shortcut_get_story_comment",
        description="Fetch one story comment (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_story_comment(ctx: Context, story_id: int, comment_id: int) -> dict[str, Any]:
        return await get_client(ctx).get(f"/stories/{_seg(str(story_id))}/comments/{_seg(str(comment_id))}")
