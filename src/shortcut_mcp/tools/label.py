"""Label read tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import (
    get_client,
    read_tags,
    shape_epic_summary,
    shape_label_summary,
    shape_story_summary,
    shaped_list,
)

_MODULE = "label"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_labels",
        description="List all labels (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_labels(ctx: Context, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/labels")
        return shaped_list(rows, shape_label_summary, limit=limit)

    @server.tool(
        name="shortcut_get_label",
        description="Fetch one label by ID (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_label(ctx: Context, label_id: int) -> dict[str, Any]:
        return await get_client(ctx).get(f"/labels/{_seg(str(label_id))}")

    @server.tool(
        name="shortcut_list_label_stories",
        description="List the stories with a label (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_label_stories(ctx: Context, label_id: int, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/labels/{_seg(str(label_id))}/stories")
        return shaped_list(rows, shape_story_summary, limit=limit)

    @server.tool(
        name="shortcut_list_label_epics",
        description="List the epics with a label (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_label_epics(ctx: Context, label_id: int, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/labels/{_seg(str(label_id))}/epics")
        return shaped_list(rows, shape_epic_summary, limit=limit)
