"""Story comment read and write tools."""

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
    shape_comment_summary,
    shaped_list,
    write_tags,
)

_MODULE = "story_comment"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False}
_DESTRUCTIVE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_story_comments",
        description="List comments on a story (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_story_comments(ctx: Context, story_id: int, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/stories/{_seg(str(story_id))}/comments")
        return shaped_list(rows, shape_comment_summary, limit=limit)

    @server.tool(
        name="shortcut_get_story_comment",
        description="Fetch one story comment (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_story_comment(ctx: Context, story_id: int, comment_id: int) -> dict[str, Any]:
        return await get_client(ctx).get(f"/stories/{_seg(str(story_id))}/comments/{_seg(str(comment_id))}")

    @server.tool(
        name="shortcut_create_story_comment",
        description="Create a comment on a story.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_create_story_comment(ctx: Context, story_id: int, text: str) -> dict[str, Any]:
        require_writes(ctx)
        return await get_client(ctx).post(f"/stories/{_seg(str(story_id))}/comments", json={"text": text})

    @server.tool(
        name="shortcut_update_story_comment",
        description="Update the text of an existing story comment.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_update_story_comment(ctx: Context, story_id: int, comment_id: int, text: str) -> dict[str, Any]:
        require_writes(ctx)
        client = get_client(ctx)
        result = await client.put(
            f"/stories/{_seg(str(story_id))}/comments/{_seg(str(comment_id))}",
            json={"text": text},
        )
        return result if result is not None else {"id": comment_id}

    @server.tool(
        name="shortcut_add_story_comment_reaction",
        description="Add an emoji reaction to a story comment.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_add_story_comment_reaction(
        ctx: Context, story_id: int, comment_id: int, emoji: str
    ) -> dict[str, Any]:
        require_writes(ctx)
        return await get_client(ctx).post(
            f"/stories/{_seg(str(story_id))}/comments/{_seg(str(comment_id))}/reactions",
            json={"emoji": emoji},
        )

    @server.tool(
        name="shortcut_remove_story_comment_reaction",
        description="Remove an emoji reaction from a story comment.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_remove_story_comment_reaction(
        ctx: Context, story_id: int, comment_id: int, emoji: str
    ) -> dict[str, Any] | None:
        require_writes(ctx)
        return await get_client(ctx).delete(
            f"/stories/{_seg(str(story_id))}/comments/{_seg(str(comment_id))}/reactions",
            json={"emoji": emoji},
        )

    @server.tool(
        name="shortcut_delete_story_comment",
        description=(
            "Permanently delete a comment on a story. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_story_comment(ctx: Context, story_id: int, comment_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/stories/{_seg(str(story_id))}/comments/{_seg(str(comment_id))}")
        return {"id": comment_id, "deleted": True}
