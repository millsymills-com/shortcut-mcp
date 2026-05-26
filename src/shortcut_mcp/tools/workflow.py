"""Workflow read tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import get_client, get_object, read_tags, shape_workflow_summary, shaped_list

_MODULE = "workflow"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_workflows",
        description="List all workflows (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_workflows(ctx: Context, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/workflows")
        return shaped_list(rows, shape_workflow_summary, limit=limit)

    @server.tool(
        name="shortcut_get_workflow",
        description="Fetch one workflow by ID (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_workflow(ctx: Context, workflow_id: int) -> dict[str, Any]:
        return await get_object(ctx, f"/workflows/{_seg(str(workflow_id))}")
