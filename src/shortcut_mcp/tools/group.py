"""Group read and write tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import (
    get_client,
    read_tags,
    require_writes,
    shape_group_summary,
    shape_story_summary,
    shaped_list,
    write_tags,
)

_MODULE = "group"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_groups",
        description="List all groups/teams (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_groups(ctx: Context, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/groups")
        return shaped_list(rows, shape_group_summary, limit=limit)

    @server.tool(
        name="shortcut_get_group",
        description="Fetch one group by UUID (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_group(ctx: Context, group_id: str) -> dict[str, Any]:
        return await get_client(ctx).get(f"/groups/{_seg(group_id)}")

    @server.tool(
        name="shortcut_list_group_stories",
        description="List the stories owned by a group (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_group_stories(ctx: Context, group_id: str, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/groups/{_seg(group_id)}/stories")
        return shaped_list(rows, shape_story_summary, limit=limit)

    @server.tool(
        name="shortcut_create_group",
        description="Create a new Shortcut group/team. Returns the created group object.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_create_group(
        ctx: Context,
        name: str,
        mention_name: str,
        description: str | None = None,
        member_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {"name": name, "mention_name": mention_name}
        if description is not None:
            body["description"] = description
        if member_ids is not None:
            body["member_ids"] = member_ids
        return await get_client(ctx).post("/groups", json=body)

    @server.tool(
        name="shortcut_update_group",
        description="Update fields on an existing Shortcut group/team.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_update_group(
        ctx: Context,
        group_id: str,
        name: str | None = None,
        mention_name: str | None = None,
        description: str | None = None,
        member_ids: list[str] | None = None,
        archived: bool | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if mention_name is not None:
            body["mention_name"] = mention_name
        if description is not None:
            body["description"] = description
        if member_ids is not None:
            body["member_ids"] = member_ids
        if archived is not None:
            body["archived"] = archived
        client = get_client(ctx)
        result = await client.put(f"/groups/{_seg(group_id)}", json=body)
        return result if result is not None else {"id": group_id}
