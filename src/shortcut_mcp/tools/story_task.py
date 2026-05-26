"""Story task read and write tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import (
    destructive_tags,
    get_client,
    read_tags,
    require_destructive,
    require_update_fields,
    require_writes,
    write_tags,
)

_MODULE = "story_task"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False}
_DESTRUCTIVE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_get_story_task",
        description="Fetch one task on a story (full object).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_story_task(ctx: Context, story_id: int, task_id: int) -> dict[str, Any]:
        return await get_client(ctx).get(f"/stories/{_seg(str(story_id))}/tasks/{_seg(str(task_id))}")

    @server.tool(
        name="shortcut_create_story_task",
        description="Create a task (checklist item) on a story.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_create_story_task(ctx: Context, story_id: int, description: str) -> dict[str, Any]:
        require_writes(ctx)
        return await get_client(ctx).post(
            f"/stories/{_seg(str(story_id))}/tasks",
            json={"description": description},
        )

    @server.tool(
        name="shortcut_update_story_task",
        description="Update a task on a story (description, completion status, or both).",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_update_story_task(
        ctx: Context,
        story_id: int,
        task_id: int,
        description: str | None = None,
        complete: bool | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {}
        if description is not None:
            body["description"] = description
        if complete is not None:
            body["complete"] = complete
        require_update_fields(body)
        client = get_client(ctx)
        result = await client.put(
            f"/stories/{_seg(str(story_id))}/tasks/{_seg(str(task_id))}",
            json=body,
        )
        return result if result is not None else {"id": task_id}

    @server.tool(
        name="shortcut_delete_story_task",
        description=(
            "Permanently delete a task on a story. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_story_task(ctx: Context, story_id: int, task_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/stories/{_seg(str(story_id))}/tasks/{_seg(str(task_id))}")
        return {"id": task_id, "deleted": True}
