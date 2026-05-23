"""Shared helpers for tool handlers.

Tool modules must NOT use TYPE_CHECKING for FastMCP imports — FastMCP
introspects type annotations at runtime. The per-file ruff ignore for
TC001/TC002 in pyproject.toml covers this.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from fastmcp import Context
from fastmcp.exceptions import ToolError

if TYPE_CHECKING:
    from collections.abc import Callable

    from shortcut_mcp.clients.shortcut import ShortcutClient
    from shortcut_mcp.server import ServerContext


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
    assert client is not None, "shortcut tools should be disabled when client is None"
    return client


def require_writes(ctx: Context) -> None:
    if not server_context(ctx).config.writes_enabled:
        raise ToolError("mode_denied: set SHORTCUT_MODE=readwrite to enable writes")


def require_destructive(ctx: Context) -> None:
    if not server_context(ctx).config.destructive_enabled:
        raise ToolError(
            "mode_denied: set SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true"
        )


def shaped_list(
    rows: list[dict[str, Any]],
    shaper: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    limit: int,
    total: int | None = None,
) -> dict[str, Any]:
    """Trim a list response to `limit` summary rows with truncation metadata."""
    truncated = len(rows) > limit
    out: dict[str, Any] = {
        "items": [shaper(r) for r in rows[:limit]],
        "truncated": truncated,
    }
    if total is not None:
        out["total"] = total
    return out
