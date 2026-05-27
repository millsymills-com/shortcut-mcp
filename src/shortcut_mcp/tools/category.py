"""Category read and write tools (CRUD + objective/milestone association lists)."""

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
    shape_category_summary,
    shape_milestone_summary,
    shaped_list,
    write_tags,
)

_MODULE = "category"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False}
_DESTRUCTIVE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_categories",
        description="List all categories (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_categories(ctx: Context, limit: LimitParam = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/categories")
        return shaped_list(rows, shape_category_summary, limit=limit)

    @server.tool(
        name="shortcut_get_category",
        description="Fetch one category by ID (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_category(ctx: Context, category_id: int) -> dict[str, Any]:
        return await get_object(ctx, f"/categories/{_seg(str(category_id))}")

    @server.tool(
        name="shortcut_list_category_milestones",
        description="List the milestones associated with a category (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_category_milestones(
        ctx: Context, category_id: int, limit: LimitParam = 50
    ) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/categories/{_seg(str(category_id))}/milestones")
        return shaped_list(rows, shape_milestone_summary, limit=limit)

    @server.tool(
        name="shortcut_list_category_objectives",
        description="List the objectives associated with a category (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_category_objectives(
        ctx: Context, category_id: int, limit: LimitParam = 50
    ) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/categories/{_seg(str(category_id))}/objectives")
        return shaped_list(rows, shape_milestone_summary, limit=limit)

    @server.tool(
        name="shortcut_create_category",
        description="Create a new category. Returns the created category object.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_create_category(
        ctx: Context,
        name: str,
        color: str | None = None,
        external_id: str | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {"name": name}
        if color is not None:
            body["color"] = color
        if external_id is not None:
            body["external_id"] = external_id
        return await get_client(ctx).post("/categories", json=body)

    @server.tool(
        name="shortcut_update_category",
        description="Update a category's name, color, or archived state.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_update_category(
        ctx: Context,
        category_id: int,
        name: str | None = None,
        color: str | None = None,
        archived: bool | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if color is not None:
            body["color"] = color
        if archived is not None:
            body["archived"] = archived
        require_update_fields(body)
        result = await get_client(ctx).put(f"/categories/{_seg(str(category_id))}", json=body)
        return result if result is not None else {"id": category_id}

    @server.tool(
        name="shortcut_delete_category",
        description=(
            "Permanently delete a category. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_category(ctx: Context, category_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/categories/{_seg(str(category_id))}")
        return {"id": category_id, "deleted": True}
