"""Project read tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import (
    get_client,
    read_tags,
    shape_project_summary,
    shape_story_summary,
    shaped_list,
)

_MODULE = "project"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_projects",
        description="List all projects (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_projects(ctx: Context, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/projects")
        return shaped_list(rows, shape_project_summary, limit=limit)

    @server.tool(
        name="shortcut_get_project",
        description="Fetch one project by ID (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_project(ctx: Context, project_id: int) -> dict[str, Any]:
        return await get_client(ctx).get(f"/projects/{_seg(str(project_id))}")

    @server.tool(
        name="shortcut_list_project_stories",
        description="List the stories in a project (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_project_stories(ctx: Context, project_id: int, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/projects/{_seg(str(project_id))}/stories")
        return shaped_list(rows, shape_story_summary, limit=limit)
