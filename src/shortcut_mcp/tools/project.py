"""Project read and write tools."""

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
    shape_project_summary,
    shape_story_summary,
    shaped_list,
    write_tags,
)

_MODULE = "project"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False}
_DESTRUCTIVE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True}


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

    @server.tool(
        name="shortcut_create_project",
        description="Create a new Shortcut project. Returns the created project object.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_create_project(
        ctx: Context,
        name: str,
        team_id: int | None = None,
        description: str | None = None,
        color: str | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {"name": name}
        if team_id is not None:
            body["team_id"] = team_id
        if description is not None:
            body["description"] = description
        if color is not None:
            body["color"] = color
        return await get_client(ctx).post("/projects", json=body)

    @server.tool(
        name="shortcut_update_project",
        description="Update fields on an existing Shortcut project.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_update_project(
        ctx: Context,
        project_id: int,
        name: str | None = None,
        description: str | None = None,
        color: str | None = None,
        archived: bool | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if color is not None:
            body["color"] = color
        if archived is not None:
            body["archived"] = archived
        client = get_client(ctx)
        result = await client.put(f"/projects/{_seg(str(project_id))}", json=body)
        return result if result is not None else {"id": project_id}

    @server.tool(
        name="shortcut_delete_project",
        description=(
            "Permanently delete a project. Irreversible. The Shortcut API rejects this "
            "with a 422 if the project still has stories — move or delete them first. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_project(ctx: Context, project_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/projects/{_seg(str(project_id))}")
        return {"id": project_id, "deleted": True}
