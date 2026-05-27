"""Custom-field read, update, and delete tools (no create — the API has none)."""

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
    shape_custom_field_summary,
    shaped_list,
    write_tags,
)

_MODULE = "custom_field"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False}
_DESTRUCTIVE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_custom_fields",
        description="List all custom fields defined in the workspace (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_custom_fields(ctx: Context, limit: LimitParam = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/custom-fields")
        return shaped_list(rows, shape_custom_field_summary, limit=limit)

    @server.tool(
        name="shortcut_get_custom_field",
        description="Fetch one custom field by ID (full object, including enum values).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_custom_field(ctx: Context, custom_field_id: str) -> dict[str, Any]:
        return await get_object(ctx, f"/custom-fields/{_seg(custom_field_id)}")

    @server.tool(
        name="shortcut_update_custom_field",
        description="Update a custom field's name, description, enabled state, or icon set.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_update_custom_field(
        ctx: Context,
        custom_field_id: str,
        name: str | None = None,
        description: str | None = None,
        enabled: bool | None = None,
        icon_set_identifier: str | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if enabled is not None:
            body["enabled"] = enabled
        if icon_set_identifier is not None:
            body["icon_set_identifier"] = icon_set_identifier
        require_update_fields(body)
        result = await get_client(ctx).put(f"/custom-fields/{_seg(custom_field_id)}", json=body)
        return result if result is not None else {"id": custom_field_id}

    @server.tool(
        name="shortcut_delete_custom_field",
        description=(
            "Permanently delete a custom field. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_custom_field(ctx: Context, custom_field_id: str) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/custom-fields/{_seg(custom_field_id)}")
        return {"id": custom_field_id, "deleted": True}
