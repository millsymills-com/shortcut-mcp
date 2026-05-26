"""Member read tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import get_client, read_tags, shape_member_summary, shaped_list

_MODULE = "member"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_members",
        description="List all members (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_members(ctx: Context, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/members")
        return shaped_list(rows, shape_member_summary, limit=limit)

    @server.tool(
        name="shortcut_get_member",
        description="Fetch one member by UUID (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_member(ctx: Context, member_id: str) -> dict[str, Any]:
        return await get_client(ctx).get(f"/members/{_seg(member_id)}")

    @server.tool(
        name="shortcut_get_current_member",
        description="Fetch the authenticated member (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_current_member(ctx: Context) -> dict[str, Any]:
        return await get_client(ctx).get("/member")
