"""Epic workflow read tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.tools._common import get_client, read_tags

_MODULE = "epic_workflow"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_get_epic_workflow",
        description="Get the epic workflow (epic states).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_epic_workflow(ctx: Context) -> dict[str, Any]:
        return await get_client(ctx).get("/epic-workflow")
