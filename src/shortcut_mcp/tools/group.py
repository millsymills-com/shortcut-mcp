"""Group read tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import (
    get_client,
    read_tags,
    shape_group_summary,
    shape_story_summary,
    shaped_list,
)

_MODULE = "group"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_groups",
        description="List all groups/teams (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_groups(ctx: Context, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/groups")
        return shaped_list(rows, shape_group_summary, limit=limit)

    @server.tool(
        name="shortcut_get_group",
        description="Fetch one group by UUID (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_group(ctx: Context, group_id: str) -> dict[str, Any]:
        return await get_client(ctx).get(f"/groups/{_seg(group_id)}")

    @server.tool(
        name="shortcut_list_group_stories",
        description="List the stories owned by a group (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_group_stories(ctx: Context, group_id: str, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/groups/{_seg(group_id)}/stories")
        return shaped_list(rows, shape_story_summary, limit=limit)
