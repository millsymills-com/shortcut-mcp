"""Console-script entry point."""

from __future__ import annotations

from shortcut_mcp._logging import configure_logging
from shortcut_mcp.server import create_server


def main() -> None:
    configure_logging()
    server = create_server()
    server.run()  # stdio transport (FastMCP default)


if __name__ == "__main__":
    main()
