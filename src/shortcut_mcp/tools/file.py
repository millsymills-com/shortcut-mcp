"""File read and write tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import (
    LimitParam,
    destructive_tags,
    get_client,
    get_object,
    read_tags,
    require_destructive,
    require_update_fields,
    require_writes,
    shape_file_summary,
    shaped_list,
    write_tags,
)

_MODULE = "file"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False}
_DESTRUCTIVE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_files",
        description="List all uploaded files (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_files(ctx: Context, limit: LimitParam = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/files")
        return shaped_list(rows, shape_file_summary, limit=limit)

    @server.tool(
        name="shortcut_get_file",
        description="Fetch one uploaded file by ID (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_file(ctx: Context, file_id: int) -> dict[str, Any]:
        return await get_object(ctx, f"/files/{_seg(str(file_id))}")

    @server.tool(
        name="shortcut_upload_file",
        description=(
            "Upload a local file to Shortcut. The server reads ANY filesystem path "
            "readable by its process and uploads the bytes. Do not expose this server "
            "to untrusted prompts when sensitive files are on disk. Requires SHORTCUT_MODE=readwrite."
        ),
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
        require_update_fields(body)
        client = get_client(ctx)
        result = await client.put(f"/files/{_seg(str(file_id))}", json=body)
        return result if result is not None else {"id": file_id}

    @server.tool(
        name="shortcut_delete_file",
        description=(
            "Permanently delete an uploaded file. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_file(ctx: Context, file_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/files/{_seg(str(file_id))}")
        return {"id": file_id, "deleted": True}
