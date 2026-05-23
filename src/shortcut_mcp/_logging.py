"""Lazy logging setup — call configure_logging() from __main__ only."""

from __future__ import annotations

import logging
import os


def configure_logging() -> None:
    """Configure root logging for the MCP server.

    Level is read from SHORTCUT_LOG_LEVEL (default INFO). Logs to stderr
    because MCP servers reserve stdout for the JSON-RPC transport.
    """
    level_name = os.environ.get("SHORTCUT_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
