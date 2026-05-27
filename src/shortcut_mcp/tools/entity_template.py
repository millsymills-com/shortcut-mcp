"""Entity (story) template read and write tools (CRUD).

Workspace-wide enable/disable of story templates is a separate admin concern
gated at the destructive tier — see tools/feature_toggle.py.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import (
    LimitParam,
    destructive_tags,
    get_client,
    get_object,
    read_tags,
    require_destructive,
    require_update_fields,
    require_writes,
    shape_entity_template_summary,
    shaped_list,
    write_tags,
)

_MODULE = "entity_template"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False}
_DESTRUCTIVE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_entity_templates",
        description="List all story templates in the workspace (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_entity_templates(ctx: Context, limit: LimitParam = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/entity-templates")
        return shaped_list(rows, shape_entity_template_summary, limit=limit)

    @server.tool(
        name="shortcut_get_entity_template",
        description="Fetch one story template by ID (full object, including story_contents).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_entity_template(ctx: Context, entity_template_id: str) -> dict[str, Any]:
        return await get_object(ctx, f"/entity-templates/{_seg(entity_template_id)}")

    @server.tool(
        name="shortcut_create_entity_template",
        description=(
            "Create a story template. story_contents is the template body "
            "(a CreateStoryContents object: story_type, name, description, tasks, labels, etc.)."
        ),
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_create_entity_template(
        ctx: Context,
        name: str,
        story_contents: dict[str, Any],
        author_id: str | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {"name": name, "story_contents": story_contents}
        if author_id is not None:
            body["author_id"] = author_id
        return await get_client(ctx).post("/entity-templates", json=body)

    @server.tool(
        name="shortcut_update_entity_template",
        description="Update a story template's name or story_contents body.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_update_entity_template(
        ctx: Context,
        entity_template_id: str,
        name: str | None = None,
        story_contents: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if story_contents is not None:
            if not story_contents:
                raise ToolError("story_contents must be a non-empty object when provided")
            body["story_contents"] = story_contents
        require_update_fields(body)
        result = await get_client(ctx).put(f"/entity-templates/{_seg(entity_template_id)}", json=body)
        return result if result is not None else {"id": entity_template_id}

    @server.tool(
        name="shortcut_delete_entity_template",
        description=(
            "Permanently delete a story template. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_entity_template(ctx: Context, entity_template_id: str) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/entity-templates/{_seg(entity_template_id)}")
        return {"id": entity_template_id, "deleted": True}
