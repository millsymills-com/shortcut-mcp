"""Epic comment read tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import get_client, read_tags, shape_comment_summary, shaped_list

_MODULE = "epic_comment"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_epic_comments",
        description="List comments on an epic (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_epic_comments(ctx: Context, epic_id: int, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/epics/{_seg(str(epic_id))}/comments")
        return shaped_list(rows, shape_comment_summary, limit=limit)

    @server.tool(
        name="shortcut_get_epic_comment",
        description="Fetch one epic comment (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_epic_comment(ctx: Context, epic_id: int, comment_id: int) -> dict[str, Any]:
        return await get_client(ctx).get(f"/epics/{_seg(str(epic_id))}/comments/{_seg(str(comment_id))}")
