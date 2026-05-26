# shortcut-mcp v0.2 Read Surface — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete read-only Shortcut tool surface (~43 tools across 17 modules) on top of the v0.1 scaffolding, plus the cross-cutting foundations (tool-profile gating, pagination, response shaping/truncation, mode-guard helper) that every later tier inherits.

**Architecture:** Keep the v0.1 split unchanged. Add foundation helpers in `clients/shortcut.py` and `tools/_common.py`, add tool-profile gating in `config.py` + `server.py`, then add one `tools/<resource>.py` module per resource group. Each tool is a thin wrapper: resolve client from `ctx`, call `client.get`/`client.paginate`, shape the result. Tests use the in-process `Client(server)` pattern from v0.1.

**Tech Stack:** Python 3.13, FastMCP (`>=3.2.4,<4.0.0`), httpx, pydantic-settings, tenacity, pytest + pytest-asyncio + respx + hypothesis, ruff, ty.

---

## Scope

**In this plan:** Phase 0 (branch) → Phase 1 (foundations) → Phase 2 (pattern-setting modules: story + search) → Phase 3 (remaining read modules, batched) → Phase 4 (wiring, tool-count smoke, CHANGELOG/README catalog stub). Mocked tests ship with every tool; property tests ship with the foundation they verify; one minimal live-smoke extension.

**Deferred to named follow-on plans (per the spec, do NOT build here):**
- `2026-05-2x-shortcut-mcp-v0.2-ci-hardening.md` — CI 3.13 matrix, CodeQL, bandit, pip-audit, coverage floor, release-install smoke.
- `2026-05-2x-shortcut-mcp-v0.2-contract-tests.md` — VCR cassette rig (`pytest-recording`) for representative payloads.
- `2026-05-2x-shortcut-mcp-v0.2-live-smoke.md` — full live-smoke split harness + nightly cron + `SHORTCUT_LIVE_WRITE_TESTS`.
- `2026-05-2x-shortcut-mcp-v0.2-community.md` — README overhaul + tool catalog generator, CONTRIBUTING/CODE_OF_CONDUCT/SECURITY, issue/PR templates, MCP registry submission, make repo public.

Multipart upload and `delete(json=…)` are **not** in this plan — their only consumers are write-tier tools (v0.3); building them now would be untestable speculation. They move to the v0.3 write plan.

## File structure

| File | Action | Responsibility |
|---|---|---|
| `src/shortcut_mcp/config.py` | modify | Add `ToolProfile` enum, `shortcut_tools`/`shortcut_profile` fields, `ALL_MODULES`/`PROFILE_MODULES` constants, `enabled_modules` property + validation. |
| `src/shortcut_mcp/clients/shortcut.py` | modify | Add `paginate()` + `_split_next()` for the `{data,next,total}` cursor family. |
| `src/shortcut_mcp/tools/_common.py` | modify | `server_context`/`get_client` accessors, `read_tags()`, `require_writes`/`require_destructive` guards, `shaped_list()` + per-resource summary shapers. |
| `src/shortcut_mcp/server.py` | modify | Module-tag gating from `config.enabled_modules`; register all read modules. |
| `src/shortcut_mcp/tools/story.py` | modify | Add `list_story_history`; adopt `_common` helpers. |
| `src/shortcut_mcp/tools/search.py` | create | `search`, `search_stories/epics/iterations/objectives`, `query_stories`. |
| `src/shortcut_mcp/tools/{story_comment,story_task,story_link,epic,epic_comment,epic_workflow,iteration,objective,member,group,workflow,label,project,file,linked_file}.py` | create | One module per resource group; read tools only. |
| `tests/test_config.py` | modify | Profile/allowlist resolution + invalid-name rejection. |
| `tests/mocked/test_client_pagination.py` | create | `paginate()` happy path + property tests. |
| `tests/mocked/test_common.py` | create | Guard helpers + `shaped_list` truncation. |
| `tests/mocked/test_tools_*.py` | create | One per tool module. |
| `tests/integration/test_live_smoke.py` | modify | Add `list_epics` + `search_stories` assertions behind existing skip. |
| `CHANGELOG.md`, `README.md` | modify | v0.2 entry + tool-catalog stub. |

---

## Phase 0 — Branch

### Task 0: Create the feature branch from origin/main

**Files:** none (git only).

- [ ] **Step 1: Branch from the clean remote base**

The spec's `main` reconciliation is verified already (backup ref `backup/local-main-2026-05-23` exists; `origin/main` squash contains all code). Branch directly from `origin/main`:

```bash
cd /Users/mills/Desktop/Projects/shortcut-mcp
git fetch origin --quiet
git switch -c feat/v0.2-read-surface origin/main
```

- [ ] **Step 2: Confirm clean base**

Run: `git status -sb && uv run pytest -q`
Expected: branch `feat/v0.2-read-surface...origin/main`, existing v0.1 tests pass.

---

## Phase 1 — Foundations

### Task 1: Tool-profile config

**Files:**
- Modify: `src/shortcut_mcp/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_config.py`:

```python
import pytest
from shortcut_mcp.config import ShortcutConfig, ToolProfile


def test_default_profile_is_core(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    cfg = ShortcutConfig()
    assert cfg.shortcut_profile is ToolProfile.CORE
    assert "story" in cfg.enabled_modules
    assert "project" not in cfg.enabled_modules  # planning-only


def test_profile_all_enables_every_module(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    cfg = ShortcutConfig()
    from shortcut_mcp.config import ALL_MODULES
    assert cfg.enabled_modules == ALL_MODULES


def test_explicit_tools_override_profile(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    monkeypatch.setenv("SHORTCUT_TOOLS", "story, epic")
    cfg = ShortcutConfig()
    assert cfg.enabled_modules == {"story", "epic"}


def test_unknown_tool_name_rejected(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_TOOLS", "story, bogus")
    with pytest.raises(ValueError, match="bogus"):
        ShortcutConfig()
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_config.py -q`
Expected: FAIL — `ToolProfile`/`ALL_MODULES`/`enabled_modules` not defined.

- [ ] **Step 3: Implement**

Add to `src/shortcut_mcp/config.py` (after the existing imports, add `from pydantic import field_validator`):

```python
class ToolProfile(enum.StrEnum):
    CORE = "core"
    PLANNING = "planning"
    FILES = "files"
    ALL = "all"


ALL_MODULES: frozenset[str] = frozenset({
    "story", "story_comment", "story_task", "story_link",
    "epic", "epic_comment", "epic_workflow",
    "iteration", "objective", "member", "group", "workflow",
    "label", "project", "file", "linked_file", "search",
})

_CORE_MODULES: frozenset[str] = frozenset({
    "story", "story_comment", "story_task", "story_link",
    "epic", "epic_comment", "epic_workflow",
    "iteration", "objective", "member", "workflow", "label", "search",
})

PROFILE_MODULES: dict[ToolProfile, frozenset[str]] = {
    ToolProfile.CORE: _CORE_MODULES,
    ToolProfile.PLANNING: _CORE_MODULES | {"group", "project"},
    ToolProfile.FILES: _CORE_MODULES | {"file", "linked_file"},
    ToolProfile.ALL: ALL_MODULES,
}
```

Add fields inside `ShortcutConfig` (after `shortcut_max_retries`):

```python
    shortcut_profile: ToolProfile = ToolProfile.CORE
    shortcut_tools: str = ""

    @field_validator("shortcut_tools")
    @classmethod
    def _validate_tools(cls, raw: str) -> str:
        names = {n.strip() for n in raw.split(",") if n.strip()}
        unknown = names - ALL_MODULES
        if unknown:
            raise ValueError(f"unknown SHORTCUT_TOOLS module(s): {sorted(unknown)}")
        return raw

    @property
    def enabled_modules(self) -> frozenset[str]:
        names = frozenset(n.strip() for n in self.shortcut_tools.split(",") if n.strip())
        return names if names else PROFILE_MODULES[self.shortcut_profile]
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_config.py -q && uv run ty check`
Expected: PASS, no type errors.

- [ ] **Step 5: Commit**

```bash
git add src/shortcut_mcp/config.py tests/test_config.py
git commit -m "feat(config): tool-profile + SHORTCUT_TOOLS module gating"
```

### Task 2: `_common` accessors, tag helper, and guards

**Files:**
- Modify: `src/shortcut_mcp/tools/_common.py`
- Test: `tests/mocked/test_common.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/mocked/test_common.py`:

```python
from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from shortcut_mcp.config import ShortcutConfig
from shortcut_mcp.server import ServerContext
from shortcut_mcp.tools._common import (
    read_tags,
    require_destructive,
    require_writes,
    shaped_list,
)


class _StubCtx:
    def __init__(self, config: ShortcutConfig) -> None:
        self.lifespan_context = ServerContext(config=config)


def _cfg(monkeypatch, **env):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return ShortcutConfig()


def test_read_tags_includes_module_and_read(monkeypatch):
    assert read_tags("epic") == {"shortcut", "read", "mod:epic"}


def test_require_writes_blocks_in_readonly(monkeypatch):
    ctx = _StubCtx(_cfg(monkeypatch, SHORTCUT_MODE="readonly"))
    with pytest.raises(ToolError, match="mode_denied"):
        require_writes(ctx)  # type: ignore[arg-type]


def test_require_writes_allows_in_readwrite(monkeypatch):
    ctx = _StubCtx(_cfg(monkeypatch, SHORTCUT_MODE="readwrite"))
    require_writes(ctx)  # type: ignore[arg-type]  # no raise


def test_require_destructive_blocks_without_flag(monkeypatch):
    ctx = _StubCtx(_cfg(monkeypatch, SHORTCUT_MODE="readwrite"))
    with pytest.raises(ToolError, match="mode_denied"):
        require_destructive(ctx)  # type: ignore[arg-type]


def test_shaped_list_truncates_and_reports(monkeypatch):
    rows = [{"id": i, "name": f"s{i}", "extra": "drop"} for i in range(5)]
    out = shaped_list(rows, lambda r: {"id": r["id"], "name": r["name"]}, limit=3, total=99)
    assert out["truncated"] is True
    assert out["total"] == 99
    assert len(out["items"]) == 3
    assert out["items"][0] == {"id": 0, "name": "s0"}
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/mocked/test_common.py -q`
Expected: FAIL — helpers not defined.

- [ ] **Step 3: Implement**

Replace `src/shortcut_mcp/tools/_common.py` with:

```python
"""Shared helpers for tool handlers.

Tool modules must NOT use TYPE_CHECKING for FastMCP imports — FastMCP
introspects type annotations at runtime. The per-file ruff ignore for
TC001/TC002 in pyproject.toml covers this.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

from fastmcp import Context
from fastmcp.exceptions import ToolError

if TYPE_CHECKING:
    from shortcut_mcp.clients.shortcut import ShortcutClient
    from shortcut_mcp.server import ServerContext


def read_tags(module: str) -> set[str]:
    """Tags for a read tool in a given resource module."""
    return {"shortcut", "read", f"mod:{module}"}


def write_tags(module: str) -> set[str]:
    return {"shortcut", "write", f"mod:{module}"}


def destructive_tags(module: str) -> set[str]:
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
```

(The old `shape_story` placeholder is removed; story summary shaping moves to Task 3.)

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/mocked/test_common.py -q && uv run ty check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/shortcut_mcp/tools/_common.py tests/mocked/test_common.py
git commit -m "feat(tools): _common accessors, tag helpers, mode guards, shaped_list"
```

### Task 3: Per-resource summary shapers

**Files:**
- Modify: `src/shortcut_mcp/tools/_common.py`
- Test: `tests/mocked/test_common.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/mocked/test_common.py`:

```python
from shortcut_mcp.tools._common import shape_story_summary, shape_member_summary


def test_shape_story_summary_picks_key_fields():
    raw = {"id": 1, "name": "S", "story_type": "feature", "workflow_state_id": 5,
           "epic_id": 9, "archived": False, "description": "x" * 9999}
    out = shape_story_summary(raw)
    assert out == {"id": 1, "name": "S", "story_type": "feature",
                   "workflow_state_id": 5, "epic_id": 9, "archived": False}


def test_shape_member_summary_flattens_profile():
    raw = {"id": "m1", "disabled": False,
           "profile": {"name": "Ada", "mention_name": "ada", "email_address": "a@b.c"}}
    out = shape_member_summary(raw)
    assert out == {"id": "m1", "disabled": False, "name": "Ada",
                   "mention_name": "ada", "email_address": "a@b.c"}


def test_shapers_tolerate_missing_optional_fields():
    assert shape_story_summary({"id": 2})["id"] == 2  # no KeyError
    assert shape_member_summary({"id": "m2"})["id"] == "m2"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/mocked/test_common.py -q`
Expected: FAIL — `shape_story_summary`/`shape_member_summary` not defined.

- [ ] **Step 3: Implement**

Add to `_common.py`:

```python
def _pick(raw: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {k: raw[k] for k in keys if k in raw}


def shape_story_summary(raw: dict[str, Any]) -> dict[str, Any]:
    return _pick(raw, ("id", "name", "story_type", "workflow_state_id",
                       "epic_id", "iteration_id", "owner_ids", "app_url", "archived"))


def shape_epic_summary(raw: dict[str, Any]) -> dict[str, Any]:
    return _pick(raw, ("id", "name", "state", "epic_state_id", "milestone_id",
                       "objective_ids", "app_url", "archived"))


def shape_iteration_summary(raw: dict[str, Any]) -> dict[str, Any]:
    return _pick(raw, ("id", "name", "status", "start_date", "end_date", "app_url"))


def shape_objective_summary(raw: dict[str, Any]) -> dict[str, Any]:
    return _pick(raw, ("id", "name", "state", "archived", "app_url"))


def shape_member_summary(raw: dict[str, Any]) -> dict[str, Any]:
    profile = raw.get("profile", {})
    out = _pick(raw, ("id", "role", "disabled"))
    out.update({k: profile[k] for k in ("name", "mention_name", "email_address") if k in profile})
    return out


def shape_group_summary(raw: dict[str, Any]) -> dict[str, Any]:
    return _pick(raw, ("id", "name", "mention_name", "archived", "member_ids"))


def shape_workflow_summary(raw: dict[str, Any]) -> dict[str, Any]:
    return _pick(raw, ("id", "name", "default_state_id", "states"))


def shape_label_summary(raw: dict[str, Any]) -> dict[str, Any]:
    return _pick(raw, ("id", "name", "color", "archived"))


def shape_project_summary(raw: dict[str, Any]) -> dict[str, Any]:
    return _pick(raw, ("id", "name", "archived", "team_id"))


def shape_file_summary(raw: dict[str, Any]) -> dict[str, Any]:
    return _pick(raw, ("id", "name", "content_type", "size", "url"))


def shape_linked_file_summary(raw: dict[str, Any]) -> dict[str, Any]:
    return _pick(raw, ("id", "name", "type", "url", "story_ids"))


def shape_comment_summary(raw: dict[str, Any]) -> dict[str, Any]:
    return _pick(raw, ("id", "author_id", "created_at", "text"))


def shape_task_summary(raw: dict[str, Any]) -> dict[str, Any]:
    return _pick(raw, ("id", "description", "complete", "story_id"))
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/mocked/test_common.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/shortcut_mcp/tools/_common.py tests/mocked/test_common.py
git commit -m "feat(tools): per-resource summary shapers"
```

### Task 4: Client `paginate()` for the cursor family

**Files:**
- Modify: `src/shortcut_mcp/clients/shortcut.py`
- Test: `tests/mocked/test_client_pagination.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/mocked/test_client_pagination.py`:

```python
from __future__ import annotations

import httpx
import pytest
import respx

from shortcut_mcp.clients.shortcut import ShortcutClient, _split_next


def test_split_next_strips_api_prefix_and_query():
    path, params = _split_next("/api/v3/search/stories?token=abc&page_size=25")
    assert path == "/search/stories"
    assert params == {"token": "abc", "page_size": "25"}


def test_split_next_rejects_absolute_url():
    with pytest.raises(ValueError, match="relative"):
        _split_next("https://evil.example/api/v3/search/stories?token=abc")


@pytest.mark.asyncio
@respx.mock
async def test_paginate_follows_next_until_exhausted():
    base = "https://api.app.shortcut.com/api/v3"
    respx.get(f"{base}/search/stories", params={"query": "x"}).mock(
        return_value=httpx.Response(200, json={"data": [{"id": 1}], "next": "/api/v3/search/stories?token=t2", "total": 2})
    )
    respx.get(f"{base}/search/stories", params={"token": "t2"}).mock(
        return_value=httpx.Response(200, json={"data": [{"id": 2}], "next": None, "total": 2})
    )
    client = ShortcutClient(token="x")
    page = await client.paginate("/search/stories", params={"query": "x"}, max_pages=5, limit=10)
    await client.close()
    assert [r["id"] for r in page["data"]] == [1, 2]
    assert page["total"] == 2


@pytest.mark.asyncio
@respx.mock
async def test_paginate_respects_max_pages():
    base = "https://api.app.shortcut.com/api/v3"
    respx.get(f"{base}/search/stories").mock(
        return_value=httpx.Response(200, json={"data": [{"id": 1}], "next": "/api/v3/search/stories?token=loop", "total": 99})
    )
    client = ShortcutClient(token="x")
    page = await client.paginate("/search/stories", params={"query": "x"}, max_pages=2, limit=1000)
    await client.close()
    assert len(page["data"]) == 2  # stopped after 2 pages despite a perpetual `next`
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/mocked/test_client_pagination.py -q`
Expected: FAIL — `_split_next`/`paginate` not defined.

- [ ] **Step 3: Implement**

Add `from urllib.parse import parse_qsl, quote, urlsplit` (extend the existing `quote` import) at the top of `clients/shortcut.py`, then add:

```python
_API_PREFIX = "/api/v3"


def _split_next(nxt: str) -> tuple[str, dict[str, str]]:
    """Parse a Shortcut `next` cursor (path + query) into a client-relative (path, params)."""
    if "://" in nxt:
        raise ValueError(f"next cursor must be relative, not absolute: {nxt!r}")
    parts = urlsplit(nxt)
    path = parts.path
    if path.startswith(_API_PREFIX):
        path = path[len(_API_PREFIX):]
    if not path.startswith("/"):
        raise ValueError(f"next cursor path must have a leading slash: {path!r}")
    return path, dict(parse_qsl(parts.query))
```

Add this method to `ShortcutClient` (after `get`):

```python
    async def paginate(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        max_pages: int = 5,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Follow the `{data, next, total}` cursor up to max_pages / limit.

        Used by /search/* and /epics/paginated. The `next` cursor is parsed into
        a relative (path, params) so the query never lands in the path.
        """
        items: list[Any] = []
        total: int | None = None
        pages = 0
        next_path, next_params = path, dict(params or {})
        while True:
            page = await self.get(next_path, params=next_params)
            items.extend(page.get("data", []))
            total = page.get("total", total)
            pages += 1
            nxt = page.get("next")
            if not nxt or pages >= max_pages or (limit is not None and len(items) >= limit):
                break
            next_path, next_params = _split_next(nxt)
        if limit is not None:
            items = items[:limit]
        return {"data": items, "total": total, "pages": pages}
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/mocked/test_client_pagination.py -q && uv run ty check`
Expected: PASS.

- [ ] **Step 5: Add a hypothesis property test for termination**

Append to `tests/mocked/test_client_pagination.py`:

```python
from hypothesis import given, settings
from hypothesis import strategies as st


@settings(max_examples=25)
@given(page_count=st.integers(min_value=1, max_value=20), cap=st.integers(min_value=1, max_value=10))
@pytest.mark.asyncio
async def test_paginate_never_exceeds_max_pages(page_count: int, cap: int):
    base = "https://api.app.shortcut.com/api/v3"
    with respx.mock:
        respx.get(f"{base}/search/stories").mock(
            return_value=httpx.Response(200, json={"data": [{"id": 1}], "next": "/api/v3/search/stories?token=t", "total": page_count})
        )
        client = ShortcutClient(token="x")
        page = await client.paginate("/search/stories", params={"query": "q"}, max_pages=cap, limit=10_000)
        await client.close()
    assert page["pages"] <= cap
```

Run: `uv run pytest tests/mocked/test_client_pagination.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/shortcut_mcp/clients/shortcut.py tests/mocked/test_client_pagination.py
git commit -m "feat(client): paginate() + next-cursor parsing for search family"
```

### Task 5: Server module-tag gating

**Files:**
- Modify: `src/shortcut_mcp/server.py`
- Test: `tests/test_server.py`

Gating is testable now with only the `story` module registered: the existing `shortcut_get_story` tag includes `mod:story` after Task 6, so an allowlist that excludes `story` must hide it. (Task 6 runs before this in execution order if you prefer; either order works since `get_story` already carries `read` tags in v0.1 — but the `mod:story` tag is added in Task 6, so **run Task 6 before Task 5**, or temporarily add `mod:story` to the v0.1 `get_story` tags first.)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_server.py`:

```python
import pytest
from fastmcp import Client

from shortcut_mcp.server import create_server


@pytest.mark.asyncio
async def test_allowlist_excluding_story_hides_get_story(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_TOOLS", "search")  # story not in allowlist
    server = create_server()
    async with Client(server) as client:
        names = {t.name for t in await client.list_tools()}
    assert "shortcut_get_story" not in names


@pytest.mark.asyncio
async def test_default_profile_includes_story(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    server = create_server()
    async with Client(server) as client:
        names = {t.name for t in await client.list_tools()}
    assert "shortcut_get_story" in names  # core profile includes story
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_server.py -k "allowlist or default_profile" -q`
Expected: FAIL — `shortcut_get_story` is present regardless of `SHORTCUT_TOOLS` (no module gating yet).

- [ ] **Step 3: Implement gating**

In `server.py`, extend the config import to `from shortcut_mcp.config import ShortcutConfig, ALL_MODULES`, and at the end of `create_server`, before `return server`:

```python
    enabled = config.enabled_modules
    for module_name in ALL_MODULES:
        if module_name not in enabled:
            server.disable(tags={f"mod:{module_name}"})
```

(The full `_register_all_tools` roster is wired in **Task 19**; until then only `story` is registered, which is enough to verify gating.)

- [ ] **Step 4: Run to verify pass + commit**

Run: `uv run pytest tests/test_server.py -q`
Expected: PASS (these two tests + existing server tests).
```bash
git add src/shortcut_mcp/server.py tests/test_server.py
git commit -m "feat(server): per-module tag gating from config.enabled_modules"
```

---

## Phase 2 — Pattern-setting modules

### Task 6: Story reads (`get_story` refit + `list_story_history`)

**Files:**
- Modify: `src/shortcut_mcp/tools/story.py`
- Test: `tests/mocked/test_tools_story.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/mocked/test_tools_story.py`:

```python
@pytest.mark.asyncio
@respx.mock
async def test_list_story_history_returns_items(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    base = "https://api.app.shortcut.com/api/v3"
    respx.get(f"{base}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{base}/stories/7/history").mock(
        return_value=httpx.Response(200, json=[{"id": "h1"}, {"id": "h2"}])
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_story_history", {"story_id": 7})
    assert not result.is_error
    assert result.data["items"][0]["id"] == "h1"
    assert result.data["truncated"] is False
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/mocked/test_tools_story.py::test_list_story_history_returns_items -q`
Expected: FAIL — tool not registered.

- [ ] **Step 3: Implement — this is the canonical read-module template**

Replace `src/shortcut_mcp/tools/story.py` with:

```python
"""Story read tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import get_client, read_tags, shaped_list

_MODULE = "story"


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_get_story",
        description="Fetch a Shortcut story by its numeric ID (full object).",
        tags=read_tags(_MODULE),
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )
    async def shortcut_get_story(ctx: Context, story_id: int) -> dict[str, Any]:
        return await get_client(ctx).get(f"/stories/{_seg(str(story_id))}")

    @server.tool(
        name="shortcut_list_story_history",
        description="List the change history for a story (most recent first).",
        tags=read_tags(_MODULE),
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )
    async def shortcut_list_story_history(
        ctx: Context, story_id: int, limit: int = 50
    ) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/stories/{_seg(str(story_id))}/history")
        return shaped_list(rows, lambda r: r, limit=limit)
```

The template, restated for reuse in Tasks 7–18:
1. `_MODULE = "<module>"` constant.
2. `register(server)` defines each tool with `@server.tool(name=, description=, tags=read_tags(_MODULE), annotations={"readOnlyHint": True, "openWorldHint": True})`.
3. `get` tools return the full object: `return await get_client(ctx).get(path)`.
4. `list` tools shape + truncate: `rows = await get_client(ctx).get(path, params=...)`; `return shaped_list(rows, shape_<resource>_summary, limit=limit)`.
5. Encode every path segment from a caller value with `_seg(str(value))`.

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/mocked/test_tools_story.py -q && uv run ty check`
Expected: PASS (both the existing `get_story` tests and the new history test).

- [ ] **Step 5: Commit**

```bash
git add src/shortcut_mcp/tools/story.py tests/mocked/test_tools_story.py
git commit -m "feat(tools): story read surface (get_story refit + list_story_history)"
```

### Task 7: Search module (most complex read module)

**Files:**
- Create: `src/shortcut_mcp/tools/search.py`
- Test: `tests/mocked/test_tools_search.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/mocked/test_tools_search.py`:

```python
from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"


@pytest.mark.asyncio
@respx.mock
async def test_search_stories_unwraps_data_envelope(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/search/stories").mock(
        return_value=httpx.Response(200, json={
            "data": [{"id": 1, "name": "A", "description": "drop"}], "next": None, "total": 1})
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_search_stories", {"query": "state:done"})
    assert not result.is_error
    assert result.data["items"] == [{"id": 1, "name": "A"}]
    assert result.data["total"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_query_stories_uses_post(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.post(f"{BASE}/stories/search").mock(
        return_value=httpx.Response(200, json=[{"id": 9, "name": "Q"}])
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_query_stories", {"archived": False})
    assert not result.is_error
    assert result.data["items"][0]["id"] == 9
```

(Note: `search_stories` summary uses `shape_story_summary`, which keeps `id` + `name` and drops `description`; that is why the first assertion expects `{"id": 1, "name": "A"}`.)

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/mocked/test_tools_search.py -q`
Expected: FAIL — search tools not registered (import error / unknown tool).

- [ ] **Step 3: Implement**

Create `src/shortcut_mcp/tools/search.py`:

```python
"""Search tools: entity search (cursor-paginated) + global + query_stories."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.tools._common import (
    get_client,
    read_tags,
    shape_epic_summary,
    shape_iteration_summary,
    shape_objective_summary,
    shape_story_summary,
    shaped_list,
)

_MODULE = "search"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}


def register(server: FastMCP) -> None:
    async def _entity_search(ctx, endpoint, query, limit, shaper):
        page = await get_client(ctx).paginate(
            endpoint, params={"query": query, "page_size": min(limit, 25)}, limit=limit
        )
        return shaped_list(page["data"], shaper, limit=limit, total=page["total"])

    @server.tool(name="shortcut_search_stories",
                 description="Search stories with Shortcut query syntax (e.g. 'state:done owner:me').",
                 tags=read_tags(_MODULE), annotations=_READ_ANN)
    async def shortcut_search_stories(ctx: Context, query: str, limit: int = 25) -> dict[str, Any]:
        return await _entity_search(ctx, "/search/stories", query, limit, shape_story_summary)

    @server.tool(name="shortcut_search_epics", description="Search epics with Shortcut query syntax.",
                 tags=read_tags(_MODULE), annotations=_READ_ANN)
    async def shortcut_search_epics(ctx: Context, query: str, limit: int = 25) -> dict[str, Any]:
        return await _entity_search(ctx, "/search/epics", query, limit, shape_epic_summary)

    @server.tool(name="shortcut_search_iterations", description="Search iterations with Shortcut query syntax.",
                 tags=read_tags(_MODULE), annotations=_READ_ANN)
    async def shortcut_search_iterations(ctx: Context, query: str, limit: int = 25) -> dict[str, Any]:
        return await _entity_search(ctx, "/search/iterations", query, limit, shape_iteration_summary)

    @server.tool(name="shortcut_search_objectives", description="Search objectives with Shortcut query syntax.",
                 tags=read_tags(_MODULE), annotations=_READ_ANN)
    async def shortcut_search_objectives(ctx: Context, query: str, limit: int = 25) -> dict[str, Any]:
        return await _entity_search(ctx, "/search/objectives", query, limit, shape_objective_summary)

    @server.tool(name="shortcut_search",
                 description="Global multi-entity search. Returns shaped stories + epics by query.",
                 tags=read_tags(_MODULE), annotations=_READ_ANN)
    async def shortcut_search(ctx: Context, query: str, limit: int = 25) -> dict[str, Any]:
        raw = await get_client(ctx).get("/search", params={"query": query, "page_size": min(limit, 25)})
        stories = (raw.get("stories") or {}).get("data", [])
        epics = (raw.get("epics") or {}).get("data", [])
        return {
            "stories": shaped_list(stories, shape_story_summary, limit=limit),
            "epics": shaped_list(epics, shape_epic_summary, limit=limit),
        }

    @server.tool(name="shortcut_query_stories",
                 description="Search stories by structured filter (POST query). Read-only despite POST.",
                 tags=read_tags(_MODULE), annotations=_READ_ANN)
    async def shortcut_query_stories(
        ctx: Context,
        archived: bool | None = None,
        owner_ids: list[str] | None = None,
        workflow_state_id: int | None = None,
        epic_id: int | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if archived is not None:
            body["archived"] = archived
        if owner_ids is not None:
            body["owner_ids"] = owner_ids
        if workflow_state_id is not None:
            body["workflow_state_id"] = workflow_state_id
        if epic_id is not None:
            body["epic_id"] = epic_id
        rows = await get_client(ctx).post("/stories/search", json=body)
        return shaped_list(rows or [], shape_story_summary, limit=limit)
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/mocked/test_tools_search.py -q && uv run ty check`
Expected: PASS.

- [ ] **Step 5: Add the search-envelope property test**

Create `tests/property/__init__.py` (empty) and `tests/property/test_invariants.py`:

```python
from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"


@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(rows=st.lists(st.fixed_dictionaries({"id": st.integers(), "name": st.text()}), max_size=40))
@pytest.mark.asyncio
async def test_search_stories_always_returns_items_envelope(monkeypatch, rows):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    with respx.mock:
        respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
        respx.get(f"{BASE}/search/stories").mock(
            return_value=httpx.Response(200, json={"data": rows, "next": None, "total": len(rows)})
        )
        server = create_server()
        async with Client(server) as client:
            result = await client.call_tool("shortcut_search_stories", {"query": "q", "limit": 25})
    assert set(result.data) >= {"items", "truncated"}
    assert len(result.data["items"]) <= 25
```

Run: `uv run pytest tests/property/test_invariants.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/shortcut_mcp/tools/search.py tests/mocked/test_tools_search.py tests/property/
git commit -m "feat(tools): search module (entity search, global, query_stories) + envelope property test"
```

---

## Phase 3 — Remaining read modules (batched)

Every task below **applies these two templates verbatim**, filling in each row of its table. No new logic — only new tools.

**Module template** (one file per `_MODULE`, e.g. `tools/epic.py`):

```python
"""<Module> read tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import get_client, read_tags, shape_epic_summary, shaped_list

_MODULE = "epic"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}


def register(server: FastMCP) -> None:
    @server.tool(name="shortcut_list_epics", description="List all epics (summary rows).",
                 tags=read_tags(_MODULE), annotations=_READ_ANN)
    async def shortcut_list_epics(ctx: Context, limit: int = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/epics")
        return shaped_list(rows, shape_epic_summary, limit=limit)

    @server.tool(name="shortcut_get_epic", description="Fetch one epic by ID (full object).",
                 tags=read_tags(_MODULE), annotations=_READ_ANN)
    async def shortcut_get_epic(ctx: Context, epic_id: int) -> dict[str, Any]:
        return await get_client(ctx).get(f"/epics/{_seg(str(epic_id))}")

    @server.tool(name="shortcut_list_epic_stories", description="List the stories in an epic (summary rows).",
                 tags=read_tags(_MODULE), annotations=_READ_ANN)
    async def shortcut_list_epic_stories(ctx: Context, epic_id: int, limit: int = 50) -> dict[str, Any]:
        from shortcut_mcp.tools._common import shape_story_summary
        rows = await get_client(ctx).get(f"/epics/{_seg(str(epic_id))}/stories")
        return shaped_list(rows, shape_story_summary, limit=limit)
```

Rules when filling a row: `get` kind → `return await get_client(ctx).get(path)`; `list` kind → `shaped_list(await get_client(ctx).get(path, params=None), <Shaper>, limit=limit)` with `limit: int = 50`. Every `{id}`/`{cid}`/`{tid}` segment is `_seg(str(<param>))`. Import only the shapers the module uses.

**Test template** (`tests/mocked/test_tools_<module>.py` — one `list` + one `get` assertion per module):

```python
from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"


@pytest.mark.asyncio
@respx.mock
async def test_list_epics_shapes_rows(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/epics").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "E", "description": "drop"}])
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_epics", {})
    assert not result.is_error
    assert result.data["items"] == [{"id": 1, "name": "E"}]
    assert result.data["truncated"] is False


@pytest.mark.asyncio
@respx.mock
async def test_get_epic_returns_full_object(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/epics/42").mock(return_value=httpx.Response(200, json={"id": 42, "name": "E"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_epic", {"epic_id": 42})
    assert not result.is_error
    assert result.data["id"] == 42
```

### Task 8: `epic`, `epic_comment`, `epic_workflow`

**Files:** Create `src/shortcut_mcp/tools/{epic,epic_comment,epic_workflow}.py`; tests `tests/mocked/test_tools_{epic,epic_comment,epic_workflow}.py`.

| Tool | `_MODULE` | Kind | Path | Params | Shaper |
|---|---|---|---|---|---|
| `shortcut_list_epics` | epic | list | `/epics` | — | `shape_epic_summary` |
| `shortcut_get_epic` | epic | get | `/epics/{id}` | `epic_id: int` | — |
| `shortcut_list_epic_stories` | epic | list | `/epics/{id}/stories` | `epic_id: int` | `shape_story_summary` |
| `shortcut_list_epic_comments` | epic_comment | list | `/epics/{id}/comments` | `epic_id: int` | `shape_comment_summary` |
| `shortcut_get_epic_comment` | epic_comment | get | `/epics/{id}/comments/{cid}` | `epic_id: int, comment_id: int` | — |
| `shortcut_get_epic_workflow` | epic_workflow | get | `/epic-workflow` | — | — |

- [ ] **Step 1:** Write `tests/mocked/test_tools_epic.py` — assert `shortcut_list_epics` returns `items`/`truncated` from a mocked `GET /epics` array, and `shortcut_get_epic` returns the full object from `GET /epics/42`. Mirror for `epic_comment`/`epic_workflow`.
- [ ] **Step 2:** Run `uv run pytest tests/mocked/test_tools_epic.py tests/mocked/test_tools_epic_comment.py tests/mocked/test_tools_epic_workflow.py -q` → FAIL.
- [ ] **Step 3:** Implement the three modules per the template + table above.
- [ ] **Step 4:** Run the same command → PASS; `uv run ty check` clean.
- [ ] **Step 5:** `git add … && git commit -m "feat(tools): epic, epic_comment, epic_workflow read tools"`

### Task 9: `iteration`, `objective`

**Files:** Create `src/shortcut_mcp/tools/{iteration,objective}.py`; matching tests.

| Tool | `_MODULE` | Kind | Path | Params | Shaper |
|---|---|---|---|---|---|
| `shortcut_list_iterations` | iteration | list | `/iterations` | — | `shape_iteration_summary` |
| `shortcut_get_iteration` | iteration | get | `/iterations/{id}` | `iteration_id: int` | — |
| `shortcut_list_iteration_stories` | iteration | list | `/iterations/{id}/stories` | `iteration_id: int` | `shape_story_summary` |
| `shortcut_list_objectives` | objective | list | `/objectives` | — | `shape_objective_summary` |
| `shortcut_get_objective` | objective | get | `/objectives/{id}` | `objective_id: int` | — |
| `shortcut_list_objective_epics` | objective | list | `/objectives/{id}/epics` | `objective_id: int` | `shape_epic_summary` |

- [ ] **Step 1:** Tests for `list_iterations` + `get_iteration` + `list_objective_epics`. → **Step 2:** FAIL → **Step 3:** implement → **Step 4:** PASS + ty → **Step 5:** commit `feat(tools): iteration + objective read tools`.

### Task 10: `member`, `group`, `workflow`

**Files:** Create `src/shortcut_mcp/tools/{member,group,workflow}.py`; matching tests.

| Tool | `_MODULE` | Kind | Path | Params | Shaper |
|---|---|---|---|---|---|
| `shortcut_list_members` | member | list | `/members` | — | `shape_member_summary` |
| `shortcut_get_member` | member | get | `/members/{id}` | `member_id: str` | — |
| `shortcut_get_current_member` | member | get | `/member` | — | — |
| `shortcut_list_groups` | group | list | `/groups` | — | `shape_group_summary` |
| `shortcut_get_group` | group | get | `/groups/{id}` | `group_id: str` | — |
| `shortcut_list_group_stories` | group | list | `/groups/{id}/stories` | `group_id: str` | `shape_story_summary` |
| `shortcut_list_workflows` | workflow | list | `/workflows` | — | `shape_workflow_summary` |
| `shortcut_get_workflow` | workflow | get | `/workflows/{id}` | `workflow_id: int` | — |

- [ ] **Step 1:** Tests including the `profile.*` flattening assertion for `list_members` (mock a member with nested `profile`, assert `name`/`mention_name` are top-level in the shaped row). → **Step 2:** FAIL → **Step 3:** implement → **Step 4:** PASS + ty → **Step 5:** commit `feat(tools): member, group, workflow read tools`.
- [ ] **Step 6:** Add the `profile.*`-nesting invariant to `tests/property/test_invariants.py` (member shaped row always exposes `name`/`mention_name` at top level when present in `profile`). Run, PASS, amend the commit or commit separately.

### Task 11: `label`, `project`

**Files:** Create `src/shortcut_mcp/tools/{label,project}.py`; matching tests.

| Tool | `_MODULE` | Kind | Path | Params | Shaper |
|---|---|---|---|---|---|
| `shortcut_list_labels` | label | list | `/labels` | — | `shape_label_summary` |
| `shortcut_get_label` | label | get | `/labels/{id}` | `label_id: int` | — |
| `shortcut_list_label_stories` | label | list | `/labels/{id}/stories` | `label_id: int` | `shape_story_summary` |
| `shortcut_list_label_epics` | label | list | `/labels/{id}/epics` | `label_id: int` | `shape_epic_summary` |
| `shortcut_list_projects` | project | list | `/projects` | — | `shape_project_summary` |
| `shortcut_get_project` | project | get | `/projects/{id}` | `project_id: int` | — |
| `shortcut_list_project_stories` | project | list | `/projects/{id}/stories` | `project_id: int` | `shape_story_summary` |

- [ ] **Step 1:** Tests for `list_labels` + `list_label_epics` + `list_project_stories`. → **Step 2:** FAIL → **Step 3:** implement → **Step 4:** PASS + ty → **Step 5:** commit `feat(tools): label + project read tools`.

### Task 12: `file`, `linked_file`, `story_comment`, `story_task`, `story_link`

**Files:** Create `src/shortcut_mcp/tools/{file,linked_file,story_comment,story_task,story_link}.py`; matching tests.

| Tool | `_MODULE` | Kind | Path | Params | Shaper |
|---|---|---|---|---|---|
| `shortcut_list_files` | file | list | `/files` | — | `shape_file_summary` |
| `shortcut_get_file` | file | get | `/files/{id}` | `file_id: int` | — |
| `shortcut_list_linked_files` | linked_file | list | `/linked-files` | — | `shape_linked_file_summary` |
| `shortcut_get_linked_file` | linked_file | get | `/linked-files/{id}` | `linked_file_id: int` | — |
| `shortcut_list_story_comments` | story_comment | list | `/stories/{id}/comments` | `story_id: int` | `shape_comment_summary` |
| `shortcut_get_story_comment` | story_comment | get | `/stories/{id}/comments/{cid}` | `story_id: int, comment_id: int` | — |
| `shortcut_get_story_task` | story_task | get | `/stories/{id}/tasks/{tid}` | `story_id: int, task_id: int` | — |
| `shortcut_get_story_link` | story_link | get | `/story-links/{id}` | `story_link_id: int` | — |

- [ ] **Step 1:** Tests for one tool per new module (`list_files`, `get_linked_file`, `list_story_comments`, `get_story_task`, `get_story_link`). → **Step 2:** FAIL → **Step 3:** implement → **Step 4:** PASS + ty → **Step 5:** commit `feat(tools): file, linked_file, story_comment, story_task, story_link read tools`.

---

## Phase 4 — Wiring & release prep

### Task 19: Wire `_register_all_tools` and assert the full surface

**Files:**
- Modify: `src/shortcut_mcp/server.py`
- Test: `tests/test_server.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_server.py`:

```python
@pytest.mark.asyncio
async def test_all_profile_exposes_full_read_surface(monkeypatch):
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    server = create_server()
    async with Client(server) as client:
        names = {t.name for t in await client.list_tools()}
    # spot-check one tool from each module is present
    for expected in [
        "shortcut_get_story", "shortcut_list_story_comments", "shortcut_get_story_task",
        "shortcut_get_story_link", "shortcut_list_epics", "shortcut_list_epic_comments",
        "shortcut_get_epic_workflow", "shortcut_list_iterations", "shortcut_list_objectives",
        "shortcut_list_members", "shortcut_list_groups", "shortcut_list_workflows",
        "shortcut_list_labels", "shortcut_list_projects", "shortcut_list_files",
        "shortcut_list_linked_files", "shortcut_search_stories",
    ]:
        assert expected in names, expected
    assert len(names) >= 40
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_server.py::test_all_profile_exposes_full_read_surface -q`
Expected: FAIL — only `shortcut_get_story*` registered.

- [ ] **Step 3: Replace `_register_all_tools` with the full read roster**

In `server.py`:

```python
def _register_all_tools(server: FastMCP) -> None:
    """Register every read module. Imported lazily to avoid circular deps."""
    from shortcut_mcp.tools import (
        epic, epic_comment, epic_workflow, file, group, iteration, label,
        linked_file, member, objective, project, search, story, story_comment,
        story_link, story_task, workflow,
    )

    for module in (
        story, story_comment, story_task, story_link, epic, epic_comment,
        epic_workflow, iteration, objective, member, group, workflow, label,
        project, file, linked_file, search,
    ):
        module.register(server)
```

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run ty check`
Expected: ALL PASS, zero lint/type warnings.

- [ ] **Step 5: Commit**

```bash
git add src/shortcut_mcp/server.py tests/test_server.py
git commit -m "feat(server): register full v0.2 read surface (17 modules)"
```

### Task 20: Live-smoke extension (minimal)

**Files:**
- Modify: `tests/integration/test_live_smoke.py`

- [ ] **Step 1: Add read assertions behind the existing skip**

Extend the existing live smoke (which already validates connection + get_story fallback) to also call `shortcut_list_epics` (assert `items` key present) and `shortcut_search_stories` with `query="is:story"` (assert no error). Reuse the existing `SHORTCUT_API_TOKEN` skip + `SHORTCUT_SMOKE_STORY_ID`/`tracer-bullet` fallback; do not add new env requirements.

- [ ] **Step 2: Run (skips without token)**

Run: `uv run pytest tests/integration -q`
Expected: SKIPPED locally (no token) or PASS against the live workspace.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_live_smoke.py
git commit -m "test(integration): extend live smoke to list_epics + search_stories"
```

### Task 21: CHANGELOG + README tool-catalog stub

**Files:**
- Modify: `CHANGELOG.md` (create if absent, Keep-a-Changelog format), `README.md`

- [ ] **Step 1:** Add an `## [Unreleased]` → `### Added` CHANGELOG entry listing the v0.2 read surface (17 modules, ~43 read tools), `SHORTCUT_PROFILE`/`SHORTCUT_TOOLS` gating, pagination + response shaping.
- [ ] **Step 2:** Add a README section: the safety/mode table, `SHORTCUT_PROFILE` values (`core` default / `planning` / `files` / `all`), and a bullet list of read tools grouped by module. (Full auto-generated catalog + community docs are the deferred community plan.)
- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md README.md
git commit -m "docs: v0.2 read surface changelog + README profiles/tool list"
```

---

## Done criteria

- `uv run pytest -q` green; `uv run ruff check . && uv run ruff format --check . && uv run ty check` clean.
- `SHORTCUT_PROFILE=all` exposes ≥40 read tools; default `core` exposes a focused subset; `SHORTCUT_TOOLS` overrides the profile; unknown module names raise at config load.
- Every list/search tool returns `{items, truncated, total?}` and respects `limit`; search follows `next` within `max_pages`.
- No write/destructive tools registered (those are v0.3/v0.4); the mode-guard helper exists and is unit-tested.
- Branch `feat/v0.2-read-surface` ready for PR (push/PR/release are the deferred CI + community plans).
