"""Epic read and write tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import (
    destructive_tags,
    get_client,
    read_tags,
    require_destructive,
    require_writes,
    shape_epic_summary,
    shape_story_summary,
    shaped_list,
    write_tags,
)

_MODULE = "epic"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False}
_DESTRUCTIVE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_epics",
        description="List all epics (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_epics(ctx: Context, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/epics")
        return shaped_list(rows, shape_epic_summary, limit=limit)

    @server.tool(
        name="shortcut_get_epic",
        description="Fetch one epic by ID (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_epic(ctx: Context, epic_id: int) -> dict[str, Any]:
        return await get_client(ctx).get(f"/epics/{_seg(str(epic_id))}")

    @server.tool(
        name="shortcut_list_epic_stories",
        description="List the stories in an epic (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_epic_stories(ctx: Context, epic_id: int, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/epics/{_seg(str(epic_id))}/stories")
        return shaped_list(rows, shape_story_summary, limit=limit)

    @server.tool(
        name="shortcut_create_epic",
        description="Create a new Shortcut epic. Returns the created epic object.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_create_epic(
        ctx: Context,
        name: str,
        description: str | None = None,
        milestone_id: int | None = None,
        owner_ids: list[str] | None = None,
        planned_start_date: str | None = None,
        deadline: str | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {"name": name}
        if description is not None:
            body["description"] = description
        if milestone_id is not None:
            body["milestone_id"] = milestone_id
        if owner_ids is not None:
            body["owner_ids"] = owner_ids
        if planned_start_date is not None:
            body["planned_start_date"] = planned_start_date
        if deadline is not None:
            body["deadline"] = deadline
        return await get_client(ctx).post("/epics", json=body)

    @server.tool(
        name="shortcut_update_epic",
        description="Update fields on an existing Shortcut epic.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_update_epic(
        ctx: Context,
        epic_id: int,
        name: str | None = None,
        description: str | None = None,
        epic_state_id: int | None = None,
        milestone_id: int | None = None,
        owner_ids: list[str] | None = None,
        deadline: str | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if epic_state_id is not None:
            body["epic_state_id"] = epic_state_id
        if milestone_id is not None:
            body["milestone_id"] = milestone_id
        if owner_ids is not None:
            body["owner_ids"] = owner_ids
        if deadline is not None:
            body["deadline"] = deadline
        client = get_client(ctx)
        result = await client.put(f"/epics/{_seg(str(epic_id))}", json=body)
        return result if result is not None else {"id": epic_id}

    @server.tool(
        name="shortcut_archive_epic",
        description="Archive a Shortcut epic (sets archived=true).",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_archive_epic(ctx: Context, epic_id: int) -> dict[str, Any]:
        require_writes(ctx)
        client = get_client(ctx)
        result = await client.put(f"/epics/{_seg(str(epic_id))}", json={"archived": True})
        return result if result is not None else {"id": epic_id}

    @server.tool(
        name="shortcut_unarchive_epic",
        description="Unarchive a Shortcut epic (sets archived=false).",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_unarchive_epic(ctx: Context, epic_id: int) -> dict[str, Any]:
        require_writes(ctx)
        client = get_client(ctx)
        result = await client.put(f"/epics/{_seg(str(epic_id))}", json={"archived": False})
        return result if result is not None else {"id": epic_id}

    @server.tool(
        name="shortcut_delete_epic",
        description=(
            "Permanently delete an epic. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_epic(ctx: Context, epic_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/epics/{_seg(str(epic_id))}")
        return {"id": epic_id, "deleted": True}
