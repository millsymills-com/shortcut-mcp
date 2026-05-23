"""Objective read and write tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import (
    get_client,
    read_tags,
    require_writes,
    shape_epic_summary,
    shape_objective_summary,
    shaped_list,
    write_tags,
)

_MODULE = "objective"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False}


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

    @server.tool(
        name="shortcut_create_objective",
        description="Create a new Shortcut objective. Returns the created objective object.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_create_objective(
        ctx: Context,
        name: str,
        description: str | None = None,
        state: str | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {"name": name}
        if description is not None:
            body["description"] = description
        if state is not None:
            body["state"] = state
        return await get_client(ctx).post("/objectives", json=body)

    @server.tool(
        name="shortcut_update_objective",
        description="Update fields on an existing Shortcut objective.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_update_objective(
        ctx: Context,
        objective_id: int,
        name: str | None = None,
        description: str | None = None,
        state: str | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if state is not None:
            body["state"] = state
        client = get_client(ctx)
        result = await client.put(f"/objectives/{_seg(str(objective_id))}", json=body)
        return result if result is not None else {"id": objective_id}
