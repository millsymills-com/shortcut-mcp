"""Key-result read and write tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import (
    get_client,
    get_object,
    read_tags,
    require_update_fields,
    require_writes,
    write_tags,
)

_MODULE = "key_result"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_get_key_result",
        description="Fetch one objective key-result by ID (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_key_result(ctx: Context, key_result_id: str) -> dict[str, Any]:
        return await get_object(ctx, f"/key-results/{_seg(key_result_id)}")

    @server.tool(
        name="shortcut_update_key_result",
        description=(
            "Update an objective key-result. Value args take a KeyResultValue object: "
            '{"numeric_value": "<decimal string>"} or {"boolean_value": <bool>}.'
        ),
        tags=write_tags(_MODULE),
        annotations=_WRITE_ANN,
    )
    async def shortcut_update_key_result(
        ctx: Context,
        key_result_id: str,
        name: str | None = None,
        observed_value: dict[str, Any] | None = None,
        initial_observed_value: dict[str, Any] | None = None,
        target_value: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if observed_value is not None:
            body["observed_value"] = observed_value
        if initial_observed_value is not None:
            body["initial_observed_value"] = initial_observed_value
        if target_value is not None:
            body["target_value"] = target_value
        require_update_fields(body)
        result = await get_client(ctx).put(f"/key-results/{_seg(key_result_id)}", json=body)
        return result if result is not None else {"id": key_result_id}
