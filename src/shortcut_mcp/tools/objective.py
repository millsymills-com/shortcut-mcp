"""Objective read tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import (
    get_client,
    read_tags,
    shape_epic_summary,
    shape_objective_summary,
    shaped_list,
)

_MODULE = "objective"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_objectives",
        description="List all objectives (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_objectives(ctx: Context, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/objectives")
        return shaped_list(rows, shape_objective_summary, limit=limit)

    @server.tool(
        name="shortcut_get_objective",
        description="Fetch one objective by ID (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_objective(ctx: Context, objective_id: int) -> dict[str, Any]:
        return await get_client(ctx).get(f"/objectives/{_seg(str(objective_id))}")

    @server.tool(
        name="shortcut_list_objective_epics",
        description="List the epics under an objective (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_objective_epics(ctx: Context, objective_id: int, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/objectives/{_seg(str(objective_id))}/epics")
        return shaped_list(rows, shape_epic_summary, limit=limit)
