"""Key-result read and write tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

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
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False}


def _validate_value(field: str, value: dict[str, Any]) -> None:
    """Reject a key-result value that is not a valid KeyResultValue.

    The API accepts exactly ``{"numeric_value": "<decimal string>"}`` or
    ``{"boolean_value": <bool>}``. An empty or mis-typed dict would otherwise slip
    past the empty-update guard as a silent no-op or surface only as a vague 400.
    """
    if set(value) == {"numeric_value"} and isinstance(value["numeric_value"], str):
        return
    if set(value) == {"boolean_value"} and isinstance(value["boolean_value"], bool):
        return
    raise ToolError(
        f'{field} must be a KeyResultValue: {{"numeric_value": "<decimal string>"}} or {{"boolean_value": <bool>}}'
    )


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
        annotations={**_WRITE_ANN, "idempotentHint": True},
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
        for field, value in (
            ("observed_value", observed_value),
            ("initial_observed_value", initial_observed_value),
            ("target_value", target_value),
        ):
            if value is not None:
                _validate_value(field, value)
                body[field] = value
        require_update_fields(body)
        result = await get_client(ctx).put(f"/key-results/{_seg(key_result_id)}", json=body)
        return result if result is not None else {"id": key_result_id}
