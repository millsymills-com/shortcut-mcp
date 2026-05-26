"""Search tools: entity search (cursor-paginated) + global + query_stories."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from shortcut_mcp.tools._common import (
    get_client,
    read_tags,
    shape_epic_summary,
    shape_iteration_summary,
    shape_objective_summary,
    shape_story_summary,
    shaped_list,
)

if TYPE_CHECKING:
    from collections.abc import Callable

_MODULE = "search"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}


async def _entity_search(
    ctx: Context,
    endpoint: str,
    query: str,
    limit: int,
    shaper: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    # page_size is capped at 25 (API max); paginate's default max_pages=5 gives a
    # ~125-item ceiling, which covers any single-call limit these tools accept.
    page = await get_client(ctx).paginate(endpoint, params={"query": query, "page_size": min(limit, 25)}, limit=limit)
    return shaped_list(page["data"], shaper, limit=limit, total=page["total"])


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_search_stories",
        description="Search stories with Shortcut query syntax (e.g. 'state:done owner:me').",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_search_stories(ctx: Context, query: str, limit: int = 25) -> dict[str, Any]:
        return await _entity_search(ctx, "/search/stories", query, limit, shape_story_summary)

    @server.tool(
        name="shortcut_search_epics",
        description="Search epics with Shortcut query syntax.",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_search_epics(ctx: Context, query: str, limit: int = 25) -> dict[str, Any]:
        return await _entity_search(ctx, "/search/epics", query, limit, shape_epic_summary)

    @server.tool(
        name="shortcut_search_iterations",
        description="Search iterations with Shortcut query syntax.",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_search_iterations(ctx: Context, query: str, limit: int = 25) -> dict[str, Any]:
        return await _entity_search(ctx, "/search/iterations", query, limit, shape_iteration_summary)

    @server.tool(
        name="shortcut_search_objectives",
        description="Search objectives with Shortcut query syntax.",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_search_objectives(ctx: Context, query: str, limit: int = 25) -> dict[str, Any]:
        return await _entity_search(ctx, "/search/objectives", query, limit, shape_objective_summary)

    @server.tool(
        name="shortcut_search",
        description=(
            "Global multi-entity search. Returns {stories: {items, truncated}, "
            "epics: {items, truncated}} — NOT a top-level items list. For a single "
            "entity use shortcut_search_stories / shortcut_search_epics."
        ),
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_search(ctx: Context, query: str, limit: int = 25) -> dict[str, Any]:
        raw = await get_client(ctx).get("/search", params={"query": query, "page_size": min(limit, 25)})
        if not isinstance(raw, dict):
            raise ToolError(f"shortcut_search: /search returned {type(raw).__name__}, expected an object")
        stories = raw.get("stories") or {}
        epics = raw.get("epics") or {}
        # Thread each entity's `total` so truncation is reported correctly when the
        # API caps the page (page_size<=25) but more results exist (limit>25).
        return {
            "stories": shaped_list(
                stories.get("data", []), shape_story_summary, limit=limit, total=stories.get("total")
            ),
            "epics": shaped_list(epics.get("data", []), shape_epic_summary, limit=limit, total=epics.get("total")),
        }

    @server.tool(
        name="shortcut_query_stories",
        description=(
            "Search stories by a structured filter. Supported filters: archived, "
            "owner_ids, workflow_state_id, epic_id (POST query; read-only despite POST)."
        ),
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_query_stories(
        ctx: Context,
        archived: bool | None = None,
        owner_ids: list[str] | None = None,
        workflow_state_id: int | None = None,
        epic_id: int | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if archived is not None:
            body["archived"] = archived
        if owner_ids is not None:
            body["owner_ids"] = owner_ids
        if workflow_state_id is not None:
            body["workflow_state_id"] = workflow_state_id
        if epic_id is not None:
            body["epic_id"] = epic_id
        rows = await get_client(ctx).post("/stories/search", json=body)
        if rows is None:
            raise ToolError("shortcut_query_stories: POST /stories/search returned an empty body")
        return shaped_list(rows, shape_story_summary, limit=limit)
