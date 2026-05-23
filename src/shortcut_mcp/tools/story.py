"""Story tools. v0.1: shortcut_get_story (the tracer bullet)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import shape_story

if TYPE_CHECKING:
    from shortcut_mcp.server import ServerContext


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_get_story",
        description="Fetch a Shortcut story by its numeric ID.",
        tags={"shortcut", "read"},
    )
    async def shortcut_get_story(ctx: Context, story_id: int) -> dict[str, Any]:
        server_ctx = cast("ServerContext", ctx.lifespan_context)
        client = server_ctx.client
        assert client is not None, "shortcut tools should be disabled when client is None"
        raw = await client.get(f"/stories/{_seg(str(story_id))}")
        return shape_story(raw)
