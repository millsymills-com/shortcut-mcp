"""Iteration read tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import (
    get_client,
    read_tags,
    shape_iteration_summary,
    shape_story_summary,
    shaped_list,
)

_MODULE = "iteration"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_iterations",
        description="List all iterations (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_iterations(ctx: Context, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/iterations")
        return shaped_list(rows, shape_iteration_summary, limit=limit)

    @server.tool(
        name="shortcut_get_iteration",
        description="Fetch one iteration by ID (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_iteration(ctx: Context, iteration_id: int) -> dict[str, Any]:
        return await get_client(ctx).get(f"/iterations/{_seg(str(iteration_id))}")

    @server.tool(
        name="shortcut_list_iteration_stories",
        description="List the stories in an iteration (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_iteration_stories(ctx: Context, iteration_id: int, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/iterations/{_seg(str(iteration_id))}/stories")
        return shaped_list(rows, shape_story_summary, limit=limit)
