# Contributing

Thanks for your interest in shortcut-mcp. This project is a FastMCP server that
exposes the Shortcut REST API as MCP tools.

## Development setup

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev
```

## Checks

Run these before opening a pull request; CI runs the same set.

```bash
uv run ruff check .            # lint
uv run ruff format --check .   # formatting
uv run ty check                # types
uv run pytest -m "not live and not live_write"   # mocked + property tests
```

The mocked suite uses `respx` and needs no credentials. Coverage must stay at or
above 90%.

### Live tests

Live tests hit a real Shortcut workspace and are skipped by default:

- `-m live` requires `SHORTCUT_API_TOKEN` (read-only smoke).
- `-m live_write` additionally requires `SHORTCUT_LIVE_WRITE_TESTS=true` and
  `SHORTCUT_TEST_WORKSPACE_TOKEN` pointing at a disposable, isolated workspace.
  Never run write/destructive tests against a workspace you care about.

## Tool gating

Tools are gated by environment, not code paths:

- `SHORTCUT_MODE=readonly` (default) exposes read tools only.
- `SHORTCUT_MODE=readwrite` adds write tools.
- Destructive (delete) tools also require `SHORTCUT_ALLOW_DESTRUCTIVE=true`.

When adding a tool, tag it (`write` / `destructive`) so the gating applies, and
add mocked tests for both the success path and the gating guard.

## Pull requests

- Branch off `main`; `main` is protected and accepts changes only via PR.
- Keep one logical change per PR. Use a clear, imperative title.
- Make sure all checks above pass locally.
