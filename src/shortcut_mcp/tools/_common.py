"""Shared helpers for tool handlers.

Tool modules must NOT use TYPE_CHECKING for FastMCP imports — FastMCP
introspects type annotations at runtime. The per-file ruff ignore for
TC001/TC002 in pyproject.toml covers this.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, cast

from fastmcp import Context
from fastmcp.exceptions import ToolError
from pydantic import Field

if TYPE_CHECKING:
    from collections.abc import Callable

    from shortcut_mcp.clients.shortcut import ShortcutClient
    from shortcut_mcp.server import ServerContext

LimitParam = Annotated[int, Field(ge=1)]
"""Page-size cap for list/search tools; rejects values below 1 at the boundary."""


def read_tags(module: str) -> set[str]:
    """Tags for a read tool in a given resource module."""
    return {"shortcut", "read", f"mod:{module}"}


def write_tags(module: str) -> set[str]:
    """Tags for a write tool in a given resource module."""
    return {"shortcut", "write", f"mod:{module}"}


def destructive_tags(module: str) -> set[str]:
    """Tags for a destructive tool in a given resource module."""
    return {"shortcut", "destructive", f"mod:{module}"}


def server_context(ctx: Context) -> ServerContext:
    return cast("ServerContext", ctx.lifespan_context)


def get_client(ctx: Context) -> ShortcutClient:
    client = server_context(ctx).client
    if client is None:
        raise ToolError("Shortcut client unavailable — startup validation failed or SHORTCUT_API_TOKEN is unset.")
    return client


async def get_object(ctx: Context, path: str) -> dict[str, Any]:
    """GET a single Shortcut object, failing clearly on an empty body.

    A missing resource is a 404 (which raises upstream), so an empty body here
    means a 204/no-content response the single-object tools can't represent —
    surface it as a clear ToolError instead of returning a null that violates
    the tool's ``dict`` output contract.
    """
    result = await get_client(ctx).get(path)
    if result is None:
        raise ToolError(f"GET {path} returned an empty body; expected a single object")
    return result


def require_writes(ctx: Context) -> None:
    if not server_context(ctx).config.writes_enabled:
        raise ToolError("mode_denied: set SHORTCUT_MODE=readwrite to enable writes")


def require_destructive(ctx: Context) -> None:
    if not server_context(ctx).config.destructive_enabled:
        raise ToolError("mode_denied: set SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true")


def require_update_fields(body: dict[str, Any]) -> None:
    """Reject an update with no fields to change.

    Every ``update_*`` tool builds its PUT body from optional args; an empty body
    would PUT ``{}`` — a silent no-op the caller almost never intends. Fail fast.
    """
    if not body:
        raise ToolError("update requires at least one field to change")


def shaped_list(
    rows: list[dict[str, Any]],
    shaper: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    limit: int,
    total: int | None = None,
) -> dict[str, Any]:
    """Trim a list response to `limit` summary rows with truncation metadata."""
    if not isinstance(rows, list):
        raise ToolError(
            f"expected a list from the Shortcut API, got {type(rows).__name__}; the response was empty or malformed"
        )
    truncated = len(rows) > limit or (total is not None and total > min(len(rows), limit))
    out: dict[str, Any] = {
        "items": [shaped for r in rows[:limit] if (shaped := shaper(r))],
        "truncated": truncated,
    }
    if total is not None:
        out["total"] = total
    return out


def _pick(raw: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    """Extract a subset of keys from a dict, omitting missing ones."""
    return {k: raw[k] for k in keys if k in raw}


def shape_story_summary(raw: dict[str, Any]) -> dict[str, Any]:
    """Pick key fields from a story for list display."""
    return _pick(
        raw,
        (
            "id",
            "name",
            "story_type",
            "workflow_state_id",
            "epic_id",
            "iteration_id",
            "owner_ids",
            "app_url",
            "archived",
        ),
    )


def shape_epic_summary(raw: dict[str, Any]) -> dict[str, Any]:
    """Pick key fields from an epic for list display."""
    return _pick(raw, ("id", "name", "state", "epic_state_id", "milestone_id", "objective_ids", "app_url", "archived"))


def shape_iteration_summary(raw: dict[str, Any]) -> dict[str, Any]:
    """Pick key fields from an iteration for list display."""
    return _pick(raw, ("id", "name", "status", "start_date", "end_date", "app_url"))


def shape_objective_summary(raw: dict[str, Any]) -> dict[str, Any]:
    """Pick key fields from an objective for list display."""
    return _pick(raw, ("id", "name", "state", "archived", "app_url"))


def shape_member_summary(raw: dict[str, Any]) -> dict[str, Any]:
    """Flatten profile nested fields and pick key fields from a member."""
    profile = raw.get("profile", {})
    out = _pick(raw, ("id", "role", "disabled"))
    out.update({k: profile[k] for k in ("name", "mention_name", "email_address") if k in profile})
    return out


def shape_group_summary(raw: dict[str, Any]) -> dict[str, Any]:
    """Pick key fields from a group for list display."""
    return _pick(raw, ("id", "name", "mention_name", "archived", "member_ids"))


def shape_workflow_summary(raw: dict[str, Any]) -> dict[str, Any]:
    """Pick key fields from a workflow for list display."""
    return _pick(raw, ("id", "name", "default_state_id", "states"))


def shape_label_summary(raw: dict[str, Any]) -> dict[str, Any]:
    """Pick key fields from a label for list display."""
    return _pick(raw, ("id", "name", "color", "archived"))


def shape_project_summary(raw: dict[str, Any]) -> dict[str, Any]:
    """Pick key fields from a project for list display."""
    return _pick(raw, ("id", "name", "archived", "team_id"))


def shape_file_summary(raw: dict[str, Any]) -> dict[str, Any]:
    """Pick key fields from a file for list display."""
    return _pick(raw, ("id", "name", "content_type", "size", "url"))


def shape_linked_file_summary(raw: dict[str, Any]) -> dict[str, Any]:
    """Pick key fields from a linked file for list display."""
    return _pick(raw, ("id", "name", "type", "url", "story_ids"))


def shape_comment_summary(raw: dict[str, Any]) -> dict[str, Any]:
    """Pick key fields from a comment for list display."""
    return _pick(raw, ("id", "author_id", "created_at", "text"))
