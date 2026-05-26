"""Epic comment read and write tools."""

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
    require_writes,
    shape_comment_summary,
    shaped_list,
    write_tags,
)

_MODULE = "epic_comment"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False}
_DESTRUCTIVE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_epic_comments",
        description="List comments on an epic (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_epic_comments(ctx: Context, epic_id: int, limit: LimitParam = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/epics/{_seg(str(epic_id))}/comments")
        return shaped_list(rows, shape_comment_summary, limit=limit)

    @server.tool(
        name="shortcut_get_epic_comment",
        description="Fetch one epic comment (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_epic_comment(ctx: Context, epic_id: int, comment_id: int) -> dict[str, Any]:
        return await get_object(ctx, f"/epics/{_seg(str(epic_id))}/comments/{_seg(str(comment_id))}")

    @server.tool(
        name="shortcut_create_epic_comment",
        description="Create a comment on an epic.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_create_epic_comment(ctx: Context, epic_id: int, text: str) -> dict[str, Any]:
        require_writes(ctx)
        return await get_client(ctx).post(f"/epics/{_seg(str(epic_id))}/comments", json={"text": text})

    @server.tool(
        name="shortcut_create_epic_comment_reply",
        description="Create a reply to an existing epic comment (POST on the comment id creates a reply).",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_create_epic_comment_reply(
        ctx: Context, epic_id: int, comment_id: int, text: str
    ) -> dict[str, Any]:
        require_writes(ctx)
        return await get_client(ctx).post(
            f"/epics/{_seg(str(epic_id))}/comments/{_seg(str(comment_id))}",
            json={"text": text},
        )

    @server.tool(
        name="shortcut_update_epic_comment",
        description="Update the text of an existing epic comment.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_update_epic_comment(ctx: Context, epic_id: int, comment_id: int, text: str) -> dict[str, Any]:
        require_writes(ctx)
        client = get_client(ctx)
        result = await client.put(
            f"/epics/{_seg(str(epic_id))}/comments/{_seg(str(comment_id))}",
            json={"text": text},
        )
        return result if result is not None else {"id": comment_id}

    @server.tool(
        name="shortcut_delete_epic_comment",
        description=(
            "Permanently delete a comment on an epic. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_epic_comment(ctx: Context, epic_id: int, comment_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/epics/{_seg(str(epic_id))}/comments/{_seg(str(comment_id))}")
        return {"id": comment_id, "deleted": True}
