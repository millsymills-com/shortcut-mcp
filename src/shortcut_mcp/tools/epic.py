"""Epic read tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import (
    get_client,
    read_tags,
    shape_epic_summary,
    shape_story_summary,
    shaped_list,
)

_MODULE = "epic"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_epics",
        description="List all epics (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_epics(ctx: Context, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/epics")
        return shaped_list(rows, shape_epic_summary, limit=limit)

    @server.tool(
        name="shortcut_get_epic",
        description="Fetch one epic by ID (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_epic(ctx: Context, epic_id: int) -> dict[str, Any]:
        return await get_client(ctx).get(f"/epics/{_seg(str(epic_id))}")

    @server.tool(
        name="shortcut_list_epic_stories",
        description="List the stories in an epic (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_epic_stories(ctx: Context, epic_id: int, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/epics/{_seg(str(epic_id))}/stories")
        return shaped_list(rows, shape_story_summary, limit=limit)
