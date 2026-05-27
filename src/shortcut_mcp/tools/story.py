"""Story read and write tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

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
    shape_story_summary,
    shaped_list,
    write_tags,
)

_MODULE = "story"
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False}
_DESTRUCTIVE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_get_story",
        description="Fetch a Shortcut story by its numeric ID.",
        tags=read_tags(_MODULE),
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )
    async def shortcut_get_story(ctx: Context, story_id: int) -> dict[str, Any]:
        return await get_object(ctx, f"/stories/{_seg(str(story_id))}")

    @server.tool(
        name="shortcut_list_story_history",
        description="List the change history for a story (most recent first).",
        tags=read_tags(_MODULE),
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )
    async def shortcut_list_story_history(ctx: Context, story_id: int, limit: LimitParam = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/stories/{_seg(str(story_id))}/history")
        return shaped_list(rows, lambda r: r, limit=limit)

    @server.tool(
        name="shortcut_list_story_sub_tasks",
        description=(
            "List a story's sub-tasks — the child stories under it (summary rows). "
            "Distinct from checklist tasks (see shortcut_get_story_task)."
        ),
        tags=read_tags(_MODULE),
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )
    async def shortcut_list_story_sub_tasks(ctx: Context, story_id: int, limit: LimitParam = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/stories/{_seg(str(story_id))}/sub-tasks")
        return shaped_list(rows, shape_story_summary, limit=limit)

    @server.tool(
        name="shortcut_create_story",
        description="Create a new Shortcut story. Returns the created story object.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_create_story(
        ctx: Context,
        name: str,
        workflow_state_id: int,
        description: str | None = None,
        epic_id: int | None = None,
        iteration_id: int | None = None,
        story_type: str | None = None,
        owner_ids: list[str] | None = None,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {"name": name, "workflow_state_id": workflow_state_id}
        if description is not None:
            body["description"] = description
        if epic_id is not None:
            body["epic_id"] = epic_id
        if iteration_id is not None:
            body["iteration_id"] = iteration_id
        if story_type is not None:
            body["story_type"] = story_type
        if owner_ids is not None:
            body["owner_ids"] = owner_ids
        if labels is not None:
            body["labels"] = [{"name": n} for n in labels]
        return await get_client(ctx).post("/stories", json=body)

    @server.tool(
        name="shortcut_update_story",
        description=(
            "Update fields on an existing Shortcut story. "
            "Replaces labels/owner_ids with the values given. "
            "To add without removing, use shortcut_add_story_labels / shortcut_add_story_owners."
        ),
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_update_story(
        ctx: Context,
        story_id: int,
        name: str | None = None,
        description: str | None = None,
        workflow_state_id: int | None = None,
        epic_id: int | None = None,
        iteration_id: int | None = None,
        story_type: str | None = None,
        archived: bool | None = None,
        owner_ids: list[str] | None = None,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if workflow_state_id is not None:
            body["workflow_state_id"] = workflow_state_id
        if epic_id is not None:
            body["epic_id"] = epic_id
        if iteration_id is not None:
            body["iteration_id"] = iteration_id
        if story_type is not None:
            body["story_type"] = story_type
        if archived is not None:
            body["archived"] = archived
        if owner_ids is not None:
            body["owner_ids"] = owner_ids
        if labels is not None:
            body["labels"] = [{"name": n} for n in labels]
        require_update_fields(body)
        client = get_client(ctx)
        result = await client.put(f"/stories/{_seg(str(story_id))}", json=body)
        return result if result is not None else {"id": story_id}

    @server.tool(
        name="shortcut_archive_story",
        description="Archive a Shortcut story (sets archived=true).",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_archive_story(ctx: Context, story_id: int) -> dict[str, Any]:
        require_writes(ctx)
        client = get_client(ctx)
        result = await client.put(f"/stories/{_seg(str(story_id))}", json={"archived": True})
        return result if result is not None else {"id": story_id}

    @server.tool(
        name="shortcut_unarchive_story",
        description="Unarchive a Shortcut story (sets archived=false).",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_unarchive_story(ctx: Context, story_id: int) -> dict[str, Any]:
        require_writes(ctx)
        client = get_client(ctx)
        result = await client.put(f"/stories/{_seg(str(story_id))}", json={"archived": False})
        return result if result is not None else {"id": story_id}

    @server.tool(
        name="shortcut_add_story_labels",
        description=(
            "Add labels to a story without removing existing ones. "
            "Fetches the current label set, merges the new names (deduplicated, order preserved), "
            "then PUTs the merged list."
        ),
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_add_story_labels(ctx: Context, story_id: int, labels: list[str]) -> dict[str, Any]:
        require_writes(ctx)
        client = get_client(ctx)
        story = await client.get(f"/stories/{_seg(str(story_id))}")
        existing_names = [lbl["name"] for lbl in story.get("labels", [])]
        merged = list(dict.fromkeys(existing_names + labels))
        result = await client.put(f"/stories/{_seg(str(story_id))}", json={"labels": [{"name": n} for n in merged]})
        return result if result is not None else {"id": story_id}

    @server.tool(
        name="shortcut_add_story_owners",
        description=(
            "Add owners to a story without removing existing ones. "
            "Fetches the current owner_ids, merges the new ids (deduplicated, order preserved), "
            "then PUTs the merged list."
        ),
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_add_story_owners(ctx: Context, story_id: int, owner_ids: list[str]) -> dict[str, Any]:
        require_writes(ctx)
        client = get_client(ctx)
        story = await client.get(f"/stories/{_seg(str(story_id))}")
        existing_ids = story.get("owner_ids", [])
        merged = list(dict.fromkeys(existing_ids + owner_ids))
        result = await client.put(f"/stories/{_seg(str(story_id))}", json={"owner_ids": merged})
        return result if result is not None else {"id": story_id}

    @server.tool(
        name="shortcut_bulk_create_stories",
        description="Create multiple Shortcut stories in a single request (POST /stories/bulk).",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_bulk_create_stories(ctx: Context, stories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        require_writes(ctx)
        return await get_client(ctx).post("/stories/bulk", json={"stories": stories})

    @server.tool(
        name="shortcut_bulk_update_stories",
        description="Update multiple Shortcut stories in a single request (PUT /stories/bulk).",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_bulk_update_stories(
        ctx: Context,
        story_ids: list[int],
        archived: bool | None = None,
        workflow_state_id: int | None = None,
        epic_id: int | None = None,
        iteration_id: int | None = None,
    ) -> list[dict[str, Any]] | None:
        require_writes(ctx)
        body: dict[str, Any] = {"story_ids": story_ids}
        if archived is not None:
            body["archived"] = archived
        if workflow_state_id is not None:
            body["workflow_state_id"] = workflow_state_id
        if epic_id is not None:
            body["epic_id"] = epic_id
        if iteration_id is not None:
            body["iteration_id"] = iteration_id
        return await get_client(ctx).put("/stories/bulk", json=body)

    @server.tool(
        name="shortcut_create_story_from_template",
        description="Create a new Shortcut story from a story template (POST /stories/from-template).",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_create_story_from_template(
        ctx: Context,
        template_id: str,
        name: str | None = None,
        description: str | None = None,
        epic_id: int | None = None,
        iteration_id: int | None = None,
        story_type: str | None = None,
        owner_ids: list[str] | None = None,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {"story_template_id": template_id}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if epic_id is not None:
            body["epic_id"] = epic_id
        if iteration_id is not None:
            body["iteration_id"] = iteration_id
        if story_type is not None:
            body["story_type"] = story_type
        if owner_ids is not None:
            body["owner_ids"] = owner_ids
        if labels is not None:
            body["labels"] = [{"name": n} for n in labels]
        return await get_client(ctx).post("/stories/from-template", json=body)

    @server.tool(
        name="shortcut_delete_story",
        description=(
            "Permanently delete a Shortcut story. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_story(ctx: Context, story_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/stories/{_seg(str(story_id))}")
        return {"id": story_id, "deleted": True}

    @server.tool(
        name="shortcut_bulk_delete_stories",
        description=(
            "Permanently delete multiple stories in one request (DELETE /stories/bulk). "
            "Irreversible. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_bulk_delete_stories(ctx: Context, story_ids: list[int]) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete("/stories/bulk", json={"story_ids": story_ids})
        return {"story_ids": story_ids, "deleted": True}
