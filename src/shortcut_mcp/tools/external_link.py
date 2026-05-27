"""External-link story read tools."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context, FastMCP
from pydantic import Field

from shortcut_mcp.tools._common import (
    LimitParam,
    get_client,
    read_tags,
    shape_story_summary,
    shaped_list,
)

_MODULE = "external_link"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}

ExternalLink = Annotated[str, Field(pattern=r"^https?://.+$", max_length=2048)]
"""An http(s) external link; matches the Shortcut API's accepted shape."""


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_external_link_stories",
        description="List the stories that reference a given external link URL (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_external_link_stories(
        ctx: Context,
        external_link: ExternalLink,
        limit: LimitParam = 50,
    ) -> dict[str, Any]:
        rows = await get_client(ctx).get("/external-link/stories", params={"external_link": external_link})
        return shaped_list(rows, shape_story_summary, limit=limit)
