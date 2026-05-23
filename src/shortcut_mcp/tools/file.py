"""File read and write tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import (
    get_client,
    read_tags,
    require_writes,
    shape_file_summary,
    shaped_list,
    write_tags,
)

_MODULE = "file"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False}


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

    @server.tool(
        name="shortcut_upload_file",
        description=("Upload a local file (server reads the given filesystem path). Requires SHORTCUT_MODE=readwrite."),
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_upload_file(ctx: Context, path: str) -> list[dict[str, Any]]:
        require_writes(ctx)
        return await get_client(ctx).upload("/files", file_path=path)

    @server.tool(
        name="shortcut_update_file",
        description="Update metadata on an existing uploaded file.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_update_file(
        ctx: Context,
        file_id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        client = get_client(ctx)
        result = await client.put(f"/files/{_seg(str(file_id))}", json=body)
        return result if result is not None else {"id": file_id}
