"""Workspace-wide feature toggles (iterations, story templates).

These flip a feature on or off for the **entire workspace** — every member is
affected, not a single entity. They carry the widest blast radius of any tool
here and are rarely scripted, so they are gated at the destructive tier
(SHORTCUT_MODE=readwrite AND SHORTCUT_ALLOW_DESTRUCTIVE=true) rather than the
ordinary write tier.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.tools._common import destructive_tags, get_client, require_destructive

_MODULE = "feature_toggle"
_TOGGLE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True}

_GATE = "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_enable_iterations",
        description=(
            f"WORKSPACE-WIDE: enable the Iterations feature for the entire workspace. Affects every member. {_GATE}"
        ),
        tags=destructive_tags(_MODULE),
        annotations=_TOGGLE_ANN,
    )
    async def shortcut_enable_iterations(ctx: Context) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).put("/iterations/enable", json={})
        return {"feature": "iterations", "enabled": True}

    @server.tool(
        name="shortcut_disable_iterations",
        description=(
            f"WORKSPACE-WIDE: disable the Iterations feature for the entire workspace. Affects every member. {_GATE}"
        ),
        tags=destructive_tags(_MODULE),
        annotations=_TOGGLE_ANN,
    )
    async def shortcut_disable_iterations(ctx: Context) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).put("/iterations/disable", json={})
        return {"feature": "iterations", "enabled": False}

    @server.tool(
        name="shortcut_enable_story_templates",
        description=(f"WORKSPACE-WIDE: enable Story Templates for the entire workspace. Affects every member. {_GATE}"),
        tags=destructive_tags(_MODULE),
        annotations=_TOGGLE_ANN,
    )
    async def shortcut_enable_story_templates(ctx: Context) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).put("/entity-templates/enable", json={})
        return {"feature": "story_templates", "enabled": True}

    @server.tool(
        name="shortcut_disable_story_templates",
        description=(
            f"WORKSPACE-WIDE: disable Story Templates for the entire workspace. Affects every member. {_GATE}"
        ),
        tags=destructive_tags(_MODULE),
        annotations=_TOGGLE_ANN,
    )
    async def shortcut_disable_story_templates(ctx: Context) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).put("/entity-templates/disable", json={})
        return {"feature": "story_templates", "enabled": False}
