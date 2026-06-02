"""Lazy logging setup — call configure_logging() from __main__ only."""

from __future__ import annotations

import json
import logging
import os
import sys


class JSONFormatter(logging.Formatter):
    """Render log records as single-line JSON objects.

    MCP servers reserve stdout for JSON-RPC transport, so structured logs go to
    stderr where a host can parse them per line.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Configure root logging for the MCP server.

    Level is read from SHORTCUT_LOG_LEVEL (default INFO). Emits structured JSON
    to stderr because MCP servers reserve stdout for the JSON-RPC transport.
    """
    level_name = os.environ.get("SHORTCUT_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(level=level, handlers=[handler])
