#!/usr/bin/env python
"""Generate the README tool catalog from the live FastMCP tool registry.

The catalog lives between marker comments in README.md. Run with no arguments
to rewrite that block in place; run with ``--check`` to exit non-zero when the
committed README is stale (CI uses this to fail on drift).

Tool name, tier, and description all come from the registered tools, so editing
a tool's ``description`` in the source is the only place the catalog text is
authored.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import SecretStr

if TYPE_CHECKING:
    from collections.abc import Iterable

from shortcut_mcp.config import ShortcutConfig, ShortcutMode, ToolProfile
from shortcut_mcp.server import create_server

README = Path(__file__).resolve().parent.parent / "README.md"
BEGIN = "<!-- BEGIN GENERATED TOOL CATALOG -->"
END = "<!-- END GENERATED TOOL CATALOG -->"

_TIERS: tuple[tuple[str, str], ...] = (("read", "Read"), ("write", "Write"), ("destructive", "Destructive"))

# A row of the catalog: (tier, module, tool name, one-line description).
_Row = tuple[str, str, str, str]


def _tier(tags: set[str]) -> str:
    if "destructive" in tags:
        return "destructive"
    if "write" in tags:
        return "write"
    return "read"


def _module(tags: set[str]) -> str:
    for tag in tags:
        if tag.startswith("mod:"):
            return tag.removeprefix("mod:")
    return "other"


def _rows(tools: Iterable[Any]) -> list[_Row]:
    rows: list[_Row] = []
    for t in tools:
        desc = (t.description or "").strip()
        if not desc:
            raise ValueError(f"tool {t.name!r} has an empty description; every catalog tool must describe itself")
        rows.append((_tier(set(t.tags)), _module(set(t.tags)), t.name, desc))
    return rows


async def _collect() -> list[_Row]:
    # A non-empty token registers the tools without authenticating; every gate is
    # opened so all three tiers are visible. list_tools() never touches the network.
    config = ShortcutConfig(
        shortcut_api_token=SecretStr("catalog"),
        shortcut_mode=ShortcutMode.READWRITE,
        shortcut_allow_destructive=True,
        shortcut_profile=ToolProfile.ALL,
    )
    return _rows(await create_server(config).list_tools())


def _render(rows: list[_Row]) -> str:
    lines: list[str] = []
    for key, label in _TIERS:
        tier_rows = [r for r in rows if r[0] == key]
        lines += [f"### {label} tools ({len(tier_rows)})", ""]
        modules: list[str] = []
        for _, module, _, _ in tier_rows:
            if module not in modules:
                modules.append(module)
        for module in modules:
            mod_rows = [r for r in tier_rows if r[1] == module]
            noun = "tool" if len(mod_rows) == 1 else "tools"
            lines += [f"#### {module} ({len(mod_rows)} {noun})", ""]
            lines += [f"- `{name}` — {desc}" for _, _, name, desc in mod_rows]
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _splice(readme: str, block: str) -> str:
    pre, begin, rest = readme.partition(BEGIN)
    if not begin:
        raise ValueError(f"{README.name} is missing the {BEGIN!r} marker")
    _, end, post = rest.partition(END)
    if not end:
        raise ValueError(f"{README.name} is missing the {END!r} marker")
    return f"{pre}{BEGIN}\n\n{block}\n{END}{post}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit non-zero if the README catalog is stale")
    args = parser.parse_args()

    block = _render(asyncio.run(_collect()))
    current = README.read_text(encoding="utf-8")
    updated = _splice(current, block)

    if args.check:
        if updated != current:
            print(
                "README tool catalog is stale. Regenerate it with:\n    uv run python scripts/generate_tool_catalog.py",
                file=sys.stderr,
            )
            return 1
        print("README tool catalog is up to date.")
        return 0

    if updated != current:
        README.write_text(updated, encoding="utf-8")
        print("Updated README tool catalog.")
    else:
        print("README tool catalog already up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
