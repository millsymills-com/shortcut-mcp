"""Linked file read tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import get_client, read_tags, shape_linked_file_summary, shaped_list

_MODULE = "linked_file"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_linked_files",
        description="List all linked files (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_linked_files(ctx: Context, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/linked-files")
        return shaped_list(rows, shape_linked_file_summary, limit=limit)

    @server.tool(
        name="shortcut_get_linked_file",
        description="Fetch one linked file by ID (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_linked_file(ctx: Context, linked_file_id: int) -> dict[str, Any]:
        return await get_client(ctx).get(f"/linked-files/{_seg(str(linked_file_id))}")
