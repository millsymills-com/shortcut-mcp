"""Label read and write tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import (
    destructive_tags,
    get_client,
    read_tags,
    require_destructive,
    require_update_fields,
    require_writes,
    shape_epic_summary,
    shape_label_summary,
    shape_story_summary,
    shaped_list,
    write_tags,
)

_MODULE = "label"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False}
_DESTRUCTIVE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_labels",
        description="List all labels (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_labels(ctx: Context, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/labels")
        return shaped_list(rows, shape_label_summary, limit=limit)

    @server.tool(
        name="shortcut_get_label",
        description="Fetch one label by ID (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_label(ctx: Context, label_id: int) -> dict[str, Any]:
        return await get_client(ctx).get(f"/labels/{_seg(str(label_id))}")

    @server.tool(
        name="shortcut_list_label_stories",
        description="List the stories with a label (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_label_stories(ctx: Context, label_id: int, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/labels/{_seg(str(label_id))}/stories")
        return shaped_list(rows, shape_story_summary, limit=limit)

    @server.tool(
        name="shortcut_list_label_epics",
        description="List the epics with a label (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_label_epics(ctx: Context, label_id: int, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/labels/{_seg(str(label_id))}/epics")
        return shaped_list(rows, shape_epic_summary, limit=limit)

    @server.tool(
        name="shortcut_create_label",
        description="Create a new Shortcut label. Returns the created label object.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_create_label(
        ctx: Context,
        name: str,
        color: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {"name": name}
        if color is not None:
            body["color"] = color
        if description is not None:
            body["description"] = description
        return await get_client(ctx).post("/labels", json=body)

    @server.tool(
        name="shortcut_update_label",
        description="Update fields on an existing Shortcut label.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_update_label(
        ctx: Context,
        label_id: int,
        name: str | None = None,
        color: str | None = None,
        description: str | None = None,
        archived: bool | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if color is not None:
            body["color"] = color
        if description is not None:
            body["description"] = description
        if archived is not None:
            body["archived"] = archived
        require_update_fields(body)
        client = get_client(ctx)
        result = await client.put(f"/labels/{_seg(str(label_id))}", json=body)
        return result if result is not None else {"id": label_id}

    @server.tool(
        name="shortcut_delete_label",
        description=(
            "Permanently delete a label. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_label(ctx: Context, label_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/labels/{_seg(str(label_id))}")
        return {"id": label_id, "deleted": True}
