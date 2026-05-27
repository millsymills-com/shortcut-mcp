"""Repository read tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import (
    LimitParam,
    get_client,
    get_object,
    read_tags,
    shape_repository_summary,
    shaped_list,
)

_MODULE = "repository"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_repositories",
        description="List all VCS repositories linked to the workspace (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_repositories(ctx: Context, limit: LimitParam = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/repositories")
        return shaped_list(rows, shape_repository_summary, limit=limit)

    @server.tool(
        name="shortcut_get_repository",
        description="Fetch one VCS repository by ID (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_repository(ctx: Context, repo_id: int) -> dict[str, Any]:
        return await get_object(ctx, f"/repositories/{_seg(str(repo_id))}")
