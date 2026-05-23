"""Iteration read and write tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import (
    get_client,
    read_tags,
    require_writes,
    shape_iteration_summary,
    shape_story_summary,
    shaped_list,
    write_tags,
)

_MODULE = "iteration"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False}


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

    @server.tool(
        name="shortcut_create_iteration",
        description="Create a new Shortcut iteration. Returns the created iteration object.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_create_iteration(
        ctx: Context,
        name: str,
        start_date: str,
        end_date: str,
        description: str | None = None,
        group_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {"name": name, "start_date": start_date, "end_date": end_date}
        if description is not None:
            body["description"] = description
        if group_ids is not None:
            body["group_ids"] = group_ids
        return await get_client(ctx).post("/iterations", json=body)

    @server.tool(
        name="shortcut_update_iteration",
        description="Update fields on an existing Shortcut iteration.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_update_iteration(
        ctx: Context,
        iteration_id: int,
        name: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if start_date is not None:
            body["start_date"] = start_date
        if end_date is not None:
            body["end_date"] = end_date
        if description is not None:
            body["description"] = description
        client = get_client(ctx)
        result = await client.put(f"/iterations/{_seg(str(iteration_id))}", json=body)
        return result if result is not None else {"id": iteration_id}
