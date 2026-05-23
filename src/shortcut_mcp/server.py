"""FastMCP server creation, lifespan, and tag-based safety gates."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

import httpx
from fastmcp import FastMCP

from shortcut_mcp.clients.shortcut import ShortcutClient
from shortcut_mcp.config import ALL_MODULES, ShortcutConfig
from shortcut_mcp.errors import ShortcutError, _classify_startup_error

logger = logging.getLogger(__name__)


@dataclass
class ServerContext:
    """Passed to tool handlers via ctx.lifespan_context."""

    config: ShortcutConfig
    client: ShortcutClient | None = field(default=None)


def _build_lifespan(config: ShortcutConfig):  # type: ignore[no-untyped-def]
    @asynccontextmanager
    async def lifespan(server: FastMCP) -> AsyncIterator[ServerContext]:
        context = ServerContext(config=config)

        if not config.authenticated:
            logger.error("Shortcut tools disabled: SHORTCUT_API_TOKEN not set (see README)")
            server.disable(tags={"shortcut"})
            yield context
            return

        assert config.shortcut_api_token is not None
        client = ShortcutClient(
            token=config.shortcut_api_token.get_secret_value(),
            base_url=config.shortcut_api_base_url,
            timeout=float(config.shortcut_request_timeout),
            max_retries=config.shortcut_max_retries,
        )

        try:
            await client.validate_connection()
        except (ShortcutError, httpx.HTTPError) as exc:
            reason = _classify_startup_error(exc)
            logger.error("Shortcut tools disabled: %s (%s)", reason, exc)
            await client.close()
            server.disable(tags={"shortcut"})
            yield context
            return

        context.client = client
        logger.info(
            "Shortcut MCP ready — mode=%s, destructive=%s",
            config.shortcut_mode.value,
            "allowed" if config.destructive_enabled else "BLOCKED",
        )

        try:
            yield context
        finally:
            try:
                await client.close()
            except (OSError, httpx.HTTPError):
                logger.exception("Error closing Shortcut client")

    return lifespan


def _register_all_tools(server: FastMCP) -> None:
    """Register every v0.1+ tool. Imported lazily to avoid circular deps."""
    from shortcut_mcp.tools.epic import register as register_epic_tools
    from shortcut_mcp.tools.epic_comment import register as register_epic_comment_tools
    from shortcut_mcp.tools.epic_workflow import register as register_epic_workflow_tools
    from shortcut_mcp.tools.search import register as register_search_tools
    from shortcut_mcp.tools.story import register as register_story_tools

    register_story_tools(server)
    register_search_tools(server)
    register_epic_tools(server)
    register_epic_comment_tools(server)
    register_epic_workflow_tools(server)


def create_server(config: ShortcutConfig | None = None) -> FastMCP:
    """Build the FastMCP instance with tools, lifespan, and tag-based gates."""
    if config is None:
        config = ShortcutConfig()

    server = FastMCP(
        name="shortcut-mcp",
        instructions=(
            "Shortcut MCP server — read workflows, epics, iterations, labels, "
            "members, and stories from a Shortcut workspace. Read-only in v0.1; "
            "writes and destructive ops are gated behind SHORTCUT_MODE and "
            "SHORTCUT_ALLOW_DESTRUCTIVE."
        ),
        lifespan=_build_lifespan(config),
    )

    _register_all_tools(server)

    if not config.writes_enabled:
        server.disable(tags={"write"})
    if not config.destructive_enabled:
        server.disable(tags={"destructive"})
    if not config.authenticated:
        server.disable(tags={"shortcut"})

    enabled = config.enabled_modules
    for module_name in ALL_MODULES:
        if module_name not in enabled:
            server.disable(tags={f"mod:{module_name}"})

    return server
