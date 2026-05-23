"""Shared helpers for tool handlers.

Tool modules must NOT use TYPE_CHECKING for FastMCP imports — FastMCP
introspects type annotations at runtime. The per-file ruff ignore for
TC001/TC002 in pyproject.toml covers this.
"""

from __future__ import annotations

from typing import Any


def shape_story(raw: dict[str, Any]) -> dict[str, Any]:
    """Strip large internal fields from a Shortcut story payload.

    v0.1 keeps everything — placeholder for v0.2 trimming.
    """
    return raw
