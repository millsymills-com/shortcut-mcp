# CLAUDE.md — Project Intelligence for shortcut-mcp

## Project Overview

Python MCP server (FastMCP) for the Shortcut REST API, packaged as an MCPB
bundle. Read/write mode separation with a default-safe readonly posture; a
further env flag gates destructive operations.

## Commands

```bash
# Install (development)
uv sync --extra dev

# Lint
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# Type check
uv run ty check src/shortcut_mcp/

# Test
uv run pytest tests/ -v

# Single test
uv run pytest tests/test_server.py -v

# Pre-commit hooks
uv run pre-commit run --all-files

# Build package
uv build
```

## Architecture

```
src/shortcut_mcp/
├── __init__.py          # Package root, exports __version__
├── __main__.py          # Entry point: creates and runs server
├── _logging.py          # Structured logging to stderr
├── server.py            # FastMCP server creation + lifespan + mode gating
├── config.py            # Pydantic settings (env vars, ShortcutMode)
├── errors.py            # Exception hierarchy + error mapping
├── clients/             # httpx async API client(s)
└── tools/               # One module per Shortcut entity (story, epic, …)
```

## Conventions

- **Python >=3.13**, strict `ty`, ruff for lint+format
- **Tool naming**: `shortcut_{verb}_{entity}` (e.g. `shortcut_get_story`,
  `shortcut_create_story`). The `shortcut_` prefix is required by PROTO-002.
- **Mode gating**: `SHORTCUT_MODE=readonly` (default) hides write tools;
  `SHORTCUT_MODE=readwrite` exposes them. `SHORTCUT_ALLOW_DESTRUCTIVE=true`
  (only meaningful in readwrite) additionally enables destructive tools.
- **Module selection**: `SHORTCUT_TOOLS` selects which entity modules register.
- **Secrets**: `SHORTCUT_API_TOKEN` is read from env only, never a CLI arg, and
  is never logged (PROTO-011/012).
- **No print statements**: log via the `logging` module to stderr.

## Canonical MCP standards

Authoritative source: `~/Desktop/Projects/consistency-check/docs/standards/`. This
repo is graded against `mcp.md` + `python.md` + `mcp-protocol.md`.

Run the audit:

```bash
cd ~/Desktop/Projects/consistency-check
uv run consistency-check audit --repo shortcut-mcp
```

## Other docs

Design specs and phase plans live under `docs/superpowers/`. Issues are tracked
as GitHub issues at `millsymills-com/shortcut-mcp` via the `gh` CLI.
