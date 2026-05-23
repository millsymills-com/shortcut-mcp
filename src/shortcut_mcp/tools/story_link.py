"""Story link read and write tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import get_client, read_tags, require_writes, write_tags

_MODULE = "story_link"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_get_story_link",
        description="Fetch one story link by ID (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_story_link(ctx: Context, story_link_id: int) -> dict[str, Any]:
        return await get_client(ctx).get(f"/story-links/{_seg(str(story_link_id))}")

    @server.tool(
        name="shortcut_create_story_link",
        description=("Create a relationship between two stories. verb must be one of: blocks, duplicates, relates to."),
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_create_story_link(ctx: Context, verb: str, subject_id: int, object_id: int) -> dict[str, Any]:
        require_writes(ctx)
        return await get_client(ctx).post(
            "/story-links",
            json={"verb": verb, "subject_id": subject_id, "object_id": object_id},
        )

    @server.tool(
        name="shortcut_update_story_link",
        description="Update the verb on an existing story link.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_update_story_link(ctx: Context, story_link_id: int, verb: str) -> dict[str, Any]:
        require_writes(ctx)
        client = get_client(ctx)
        result = await client.put(f"/story-links/{_seg(str(story_link_id))}", json={"verb": verb})
        return result if result is not None else {"id": story_link_id}
