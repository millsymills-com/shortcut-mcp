"""Epic and objective health read and write tools."""

from __future__ import annotations

from typing import Any, Literal

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import (
    LimitParam,
    get_client,
    get_object,
    read_tags,
    require_update_fields,
    require_writes,
    shape_health_summary,
    shaped_list,
    write_tags,
)

_MODULE = "health"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False}

HealthStatus = Literal["At Risk", "On Track", "Off Track", "No Health"]
"""The four health states the API accepts."""


def _reject_empty_text(text: str, *, empty_hint: str) -> None:
    if not text.strip():
        raise ToolError(f"text must be non-empty when provided ({empty_hint})")


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_get_epic_health",
        description="Fetch an epic's current health (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_epic_health(ctx: Context, epic_id: int) -> dict[str, Any]:
        return await get_object(ctx, f"/epics/{_seg(str(epic_id))}/health")

    @server.tool(
        name="shortcut_list_epic_health_history",
        description="List an epic's health history, most recent first (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_epic_health_history(ctx: Context, epic_id: int, limit: LimitParam = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/epics/{_seg(str(epic_id))}/health-history")
        return shaped_list(rows, shape_health_summary, limit=limit)

    @server.tool(
        name="shortcut_create_epic_health",
        description="Set an epic's health status (At Risk / On Track / Off Track / No Health), with optional text.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_create_epic_health(
        ctx: Context, epic_id: int, status: HealthStatus, text: str | None = None
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {"status": status}
        if text is not None:
            _reject_empty_text(text, empty_hint="omit it to leave the note empty")
            body["text"] = text
        return await get_client(ctx).post(f"/epics/{_seg(str(epic_id))}/health", json=body)

    @server.tool(
        name="shortcut_get_objective_health",
        description="Fetch an objective's current health (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_objective_health(ctx: Context, objective_id: int) -> dict[str, Any]:
        return await get_object(ctx, f"/objectives/{_seg(str(objective_id))}/health")

    @server.tool(
        name="shortcut_list_objective_health_history",
        description="List an objective's health history, most recent first (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_objective_health_history(
        ctx: Context, objective_id: int, limit: LimitParam = 50
    ) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/objectives/{_seg(str(objective_id))}/health-history")
        return shaped_list(rows, shape_health_summary, limit=limit)

    @server.tool(
        name="shortcut_create_objective_health",
        description="Set an objective's health (At Risk / On Track / Off Track / No Health), with optional text.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_create_objective_health(
        ctx: Context, objective_id: int, status: HealthStatus, text: str | None = None
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {"status": status}
        if text is not None:
            _reject_empty_text(text, empty_hint="omit it to leave the note empty")
            body["text"] = text
        return await get_client(ctx).post(f"/objectives/{_seg(str(objective_id))}/health", json=body)

    @server.tool(
        name="shortcut_update_health",
        description="Update an existing health entry's status and/or text by its health ID.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_update_health(
        ctx: Context, health_id: str, status: HealthStatus | None = None, text: str | None = None
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {}
        if status is not None:
            body["status"] = status
        if text is not None:
            _reject_empty_text(text, empty_hint="omit it to leave the note unchanged")
            body["text"] = text
        require_update_fields(body)
        result = await get_client(ctx).put(f"/health/{_seg(health_id)}", json=body)
        return result if result is not None else {"id": health_id}
