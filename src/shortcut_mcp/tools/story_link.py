"""Story link read tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import get_client, read_tags

_MODULE = "story_link"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_get_story_link",
        description="Fetch one story link by ID (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_story_link(ctx: Context, story_link_id: int) -> dict[str, Any]:
        return await get_client(ctx).get(f"/story-links/{_seg(str(story_link_id))}")
