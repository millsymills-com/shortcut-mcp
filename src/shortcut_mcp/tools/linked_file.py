"""Linked file read and write tools."""

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
    shape_linked_file_summary,
    shaped_list,
    write_tags,
)

_MODULE = "linked_file"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False}
_DESTRUCTIVE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_linked_files",
        description="List all linked files (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_linked_files(ctx: Context, limit: LimitParam = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/linked-files")
        return shaped_list(rows, shape_linked_file_summary, limit=limit)

    @server.tool(
        name="shortcut_get_linked_file",
        description="Fetch one linked file by ID (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_linked_file(ctx: Context, linked_file_id: int) -> dict[str, Any]:
        return await get_object(ctx, f"/linked-files/{_seg(str(linked_file_id))}")

    @server.tool(
        name="shortcut_create_linked_file",
        description="Create a new Shortcut linked file. Returns the created linked file object.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_create_linked_file(
        ctx: Context,
        name: str,
        url: str,
        type: str,
        description: str | None = None,
        story_id: int | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {"name": name, "url": url, "type": type}
        if description is not None:
            body["description"] = description
        if story_id is not None:
            body["story_id"] = story_id
        return await get_client(ctx).post("/linked-files", json=body)

    @server.tool(
        name="shortcut_update_linked_file",
        description="Update fields on an existing Shortcut linked file.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_update_linked_file(
        ctx: Context,
        linked_file_id: int,
        name: str | None = None,
        url: str | None = None,
        type: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if url is not None:
            body["url"] = url
        if type is not None:
            body["type"] = type
        if description is not None:
            body["description"] = description
        require_update_fields(body)
        client = get_client(ctx)
        result = await client.put(f"/linked-files/{_seg(str(linked_file_id))}", json=body)
        return result if result is not None else {"id": linked_file_id}

    @server.tool(
        name="shortcut_delete_linked_file",
        description=(
            "Permanently delete a linked file. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_linked_file(ctx: Context, linked_file_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/linked-files/{_seg(str(linked_file_id))}")
        return {"id": linked_file_id, "deleted": True}
