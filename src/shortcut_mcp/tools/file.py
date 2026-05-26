"""File read tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import get_client, read_tags, shape_file_summary, shaped_list

_MODULE = "file"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_files",
        description="List all uploaded files (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_files(ctx: Context, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/files")
        return shaped_list(rows, shape_file_summary, limit=limit)

    @server.tool(
        name="shortcut_get_file",
        description="Fetch one uploaded file by ID (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_file(ctx: Context, file_id: int) -> dict[str, Any]:
        return await get_client(ctx).get(f"/files/{_seg(str(file_id))}")
