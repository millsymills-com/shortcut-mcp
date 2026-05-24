# shortcut-mcp v0.4 Destructive Tier — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the 13 destructive `delete_*` tools across the core resource modules, gated behind `SHORTCUT_MODE=readwrite` **and** `SHORTCUT_ALLOW_DESTRUCTIVE=true`, on top of the v0.3 write tier.

**Architecture:** Pure-additive. Every destructive scaffold already exists from v0.2: `ShortcutClient.delete(path, *, json=None)`, the `destructive_tags(module)` tag helper, the `require_destructive(ctx)` runtime guard (already unit-tested in `tests/mocked/test_common.py`), and the post-registration `server.disable(tags={"destructive"})` gate. Each task adds `delete_*` handlers to a module's existing `register()` — tagged `destructive_tags(_MODULE)`, calling `require_destructive(ctx)` first, returning a synthetic `{"id": …, "deleted": True}` confirmation because Shortcut DELETEs return `204 No Content`. No client, config, or `_register_all_tools` changes.

**Tech Stack:** Python 3.13, FastMCP, httpx, pytest/respx/hypothesis, ruff, ty.

---

## Scope

**In:** 13 `delete_*` tools (incl. `bulk_delete_stories` via `DELETE /stories/bulk` with a `{story_ids}` body); per-tool mocked tests run with `SHORTCUT_MODE=readwrite` + `SHORTCUT_ALLOW_DESTRUCTIVE=true`; server-visibility tests (deletes hidden unless destructive enabled; full 94-tool surface when enabled); an **opt-in, skip-by-default** live destructive harness against an **isolated** workspace token; README + CHANGELOG.

**Out (later tiers/issues):** niche resources (v0.5, #5); CI/VCR harness (#6/#7); the broader live-write nightly split (only the opt-in disposable-fixture harness lands here). No `delete_group` — the Shortcut API has no `DELETE /groups/{id}` endpoint.

**Design decisions (locked):**
- **Confirmation return shape.** DELETE returns `204`/empty → `client.delete` returns `None`. Handlers return `{"id": <id>, "deleted": True}` (or `{"story_ids": [...], "deleted": True}` for bulk) so MCP clients get a structured, non-null result.
- **Idempotency hint `True`.** Re-deleting a gone resource is a no-op end-state (the API 404s, surfaced as a `ToolError`), so `destructiveHint=True, idempotentHint=True`.
- **No new list/read tools.** Deletes mirror the exact resource paths already used by the v0.2 read tools — no new endpoints.
- **`delete_project` constraint stays in the tool description, not enforced client-side.** Shortcut rejects deleting a project that still has stories (`422`); the existing client maps that to `ShortcutClientError` → `ToolError`, which is the correct surfacing. Don't pre-check.
- **Live destructive tests never touch the nightly read token.** They require a *separate* env var `SHORTCUT_TEST_WORKSPACE_TOKEN` **and** `SHORTCUT_LIVE_WRITE_TESTS=true`; absent either, they skip. They create their own disposable fixtures and delete them.

## File structure

| File | Action | Responsibility |
|---|---|---|
| `tools/story.py` | modify | add `delete_story`, `bulk_delete_stories` |
| `tools/story_comment.py` | modify | add `delete_story_comment` |
| `tools/story_task.py` | modify | add `delete_story_task` |
| `tools/story_link.py` | modify | add `delete_story_link` |
| `tools/epic.py` | modify | add `delete_epic` |
| `tools/epic_comment.py` | modify | add `delete_epic_comment` |
| `tools/iteration.py` | modify | add `delete_iteration` |
| `tools/objective.py` | modify | add `delete_objective` |
| `tools/label.py` | modify | add `delete_label` |
| `tools/project.py` | modify | add `delete_project` |
| `tools/file.py` | modify | add `delete_file` |
| `tools/linked_file.py` | modify | add `delete_linked_file` |
| `tests/mocked/test_tools_*.py` | modify | one mocked test per delete tool (destructive enabled) |
| `tests/test_server.py` | modify | destructive visibility: hidden w/o flag (count 81), full surface w/ flag (count 94) |
| `tests/integration/test_live_destructive.py` | create | opt-in disposable-fixture live delete, skip-by-default |
| `tests/conftest.py` | modify | `live_write_token` fixture (isolated token + opt-in flag) |
| `pyproject.toml` | modify | add `live_write` pytest marker |
| `CHANGELOG.md`, `README.md` | modify | v0.4 entry; safety table adds the destructive row |

## Tool inventory (destructive tier — 13)

| Module | Tool | Method + path |
|---|---|---|
| story | `delete_story` | `DELETE /stories/{id}` |
| story | `bulk_delete_stories` | `DELETE /stories/bulk` body `{story_ids}` |
| story_comment | `delete_story_comment` | `DELETE /stories/{sid}/comments/{cid}` |
| story_task | `delete_story_task` | `DELETE /stories/{sid}/tasks/{tid}` |
| story_link | `delete_story_link` | `DELETE /story-links/{id}` |
| epic | `delete_epic` | `DELETE /epics/{id}` |
| epic_comment | `delete_epic_comment` | `DELETE /epics/{eid}/comments/{cid}` |
| iteration | `delete_iteration` | `DELETE /iterations/{id}` |
| objective | `delete_objective` | `DELETE /objectives/{id}` |
| label | `delete_label` | `DELETE /labels/{id}` |
| project | `delete_project` | `DELETE /projects/{id}` (422 if non-empty) |
| file | `delete_file` | `DELETE /files/{id}` |
| linked_file | `delete_linked_file` | `DELETE /linked-files/{id}` |

Full surface when destructive enabled (`profile=all`): **43 read + 38 write + 13 destructive = 94 tools**.

---

## Phase 1 — Story deletes (pattern-setter)

### Task 1: `delete_story` + `bulk_delete_stories`

**Files:**
- Modify: `src/shortcut_mcp/tools/story.py`
- Test: `tests/mocked/test_tools_story.py`

Establishes the **destructive-handler template** every later task copies:

```python
from shortcut_mcp.tools._common import (
    destructive_tags,
    get_client,
    read_tags,
    require_destructive,
    require_writes,
    shaped_list,
    write_tags,
)

_DESTRUCTIVE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True}
```

Rules: every destructive handler calls `require_destructive(ctx)` first; tag with `destructive_tags(_MODULE)`; annotate with `_DESTRUCTIVE_ANN`; the description must say it is irreversible and name both env gates; return `{"id": <id>, "deleted": True}`.

- [ ] **Step 1 — Write the failing tests.** Append to `tests/mocked/test_tools_story.py` (the file already imports `json`, `httpx`, `pytest`, `respx`, `Client`, `create_server`, and defines `BASE`):

```python
@pytest.mark.asyncio
@respx.mock
async def test_delete_story_calls_delete_and_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/stories/7").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_story", {"story_id": 7})
    assert not result.is_error
    assert result.data == {"id": 7, "deleted": True}
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_bulk_delete_stories_sends_ids_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/stories/bulk").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_bulk_delete_stories", {"story_ids": [1, 2, 3]})
    assert not result.is_error
    assert result.data == {"story_ids": [1, 2, 3], "deleted": True}
    body = json.loads(route.calls.last.request.content)
    assert body == {"story_ids": [1, 2, 3]}


@pytest.mark.asyncio
@respx.mock
async def test_delete_story_hidden_without_destructive_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")  # writes on, destructive OFF
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    server = create_server()
    async with Client(server) as client:
        names = {t.name for t in await client.list_tools()}
    assert "shortcut_delete_story" not in names
```

- [ ] **Step 2 — Run, verify FAIL.**
  Run: `cd ~/Desktop/Projects/shortcut-mcp && uv run pytest tests/mocked/test_tools_story.py -k delete -v`
  Expected: FAIL — `shortcut_delete_story` / `shortcut_bulk_delete_stories` not found.

- [ ] **Step 3 — Implement.** Add the import line change (above) and append these handlers inside `register()` in `tools/story.py`:

```python
    @server.tool(
        name="shortcut_delete_story",
        description=(
            "Permanently delete a Shortcut story. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_story(ctx: Context, story_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/stories/{_seg(str(story_id))}")
        return {"id": story_id, "deleted": True}

    @server.tool(
        name="shortcut_bulk_delete_stories",
        description=(
            "Permanently delete multiple stories in one request (DELETE /stories/bulk). "
            "Irreversible. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_bulk_delete_stories(ctx: Context, story_ids: list[int]) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete("/stories/bulk", json={"story_ids": story_ids})
        return {"story_ids": story_ids, "deleted": True}
```

- [ ] **Step 4 — Run, verify PASS + gates.**
  Run: `uv run pytest tests/mocked/test_tools_story.py -v && uv run ruff check . && uv run ruff format --check . && uv run ty check`
  Expected: PASS, clean.

- [ ] **Step 5 — Commit.**
  `git add src/shortcut_mcp/tools/story.py tests/mocked/test_tools_story.py && git commit -m "feat(tools): story delete + bulk-delete destructive tools"`

---

## Phase 2 — Remaining delete modules (batched)

Each task: add the `delete_*` handler(s) to the module's existing `register()`, extend its `_common` import with `destructive_tags, require_destructive`, define `_DESTRUCTIVE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True}` near the module's `_WRITE_ANN`, add one mocked test per tool (with `SHORTCUT_MODE=readwrite` + `SHORTCUT_ALLOW_DESTRUCTIVE=true`), run gates, commit. Paths mirror the existing read tools exactly.

### Task 2: story_comment + story_task + story_link deletes

**Files:** `tools/story_comment.py`, `tools/story_task.py`, `tools/story_link.py`; matching `tests/mocked/test_tools_*.py`.

- [ ] **Step 1 — Failing tests.** Append to each module's test file (each already defines `BASE` and imports `json`/`httpx`/`pytest`/`respx`/`Client`/`create_server`):

```python
# tests/mocked/test_tools_story_comment.py
@pytest.mark.asyncio
@respx.mock
async def test_delete_story_comment_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/stories/5/comments/9").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_story_comment", {"story_id": 5, "comment_id": 9})
    assert not result.is_error
    assert result.data == {"id": 9, "deleted": True}
    assert route.called
```
```python
# tests/mocked/test_tools_story_task.py
@pytest.mark.asyncio
@respx.mock
async def test_delete_story_task_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/stories/5/tasks/3").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_story_task", {"story_id": 5, "task_id": 3})
    assert not result.is_error
    assert result.data == {"id": 3, "deleted": True}
    assert route.called
```
```python
# tests/mocked/test_tools_story_link.py
@pytest.mark.asyncio
@respx.mock
async def test_delete_story_link_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/story-links/4").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_story_link", {"story_link_id": 4})
    assert not result.is_error
    assert result.data == {"id": 4, "deleted": True}
    assert route.called
```

- [ ] **Step 2 — Run, FAIL.** `uv run pytest tests/mocked/test_tools_story_comment.py tests/mocked/test_tools_story_task.py tests/mocked/test_tools_story_link.py -k delete -v`

- [ ] **Step 3 — Implement.** Add handlers (and the import + `_DESTRUCTIVE_ANN` line) to each module:

```python
# tools/story_comment.py
    @server.tool(
        name="shortcut_delete_story_comment",
        description=(
            "Permanently delete a comment on a story. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_story_comment(ctx: Context, story_id: int, comment_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/stories/{_seg(str(story_id))}/comments/{_seg(str(comment_id))}")
        return {"id": comment_id, "deleted": True}
```
```python
# tools/story_task.py
    @server.tool(
        name="shortcut_delete_story_task",
        description=(
            "Permanently delete a task on a story. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_story_task(ctx: Context, story_id: int, task_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/stories/{_seg(str(story_id))}/tasks/{_seg(str(task_id))}")
        return {"id": task_id, "deleted": True}
```
```python
# tools/story_link.py
    @server.tool(
        name="shortcut_delete_story_link",
        description=(
            "Permanently delete a story link. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_story_link(ctx: Context, story_link_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/story-links/{_seg(str(story_link_id))}")
        return {"id": story_link_id, "deleted": True}
```

- [ ] **Step 4 — PASS + gates.** `uv run pytest tests/mocked/ -q && uv run ruff check . && uv run ruff format --check . && uv run ty check`
- [ ] **Step 5 — Commit.** `feat(tools): story_comment/task/link delete tools`

### Task 3: epic + epic_comment deletes

**Files:** `tools/epic.py`, `tools/epic_comment.py`; matching test files.

- [ ] **Step 1 — Failing tests.**
```python
# tests/mocked/test_tools_epic.py
@pytest.mark.asyncio
@respx.mock
async def test_delete_epic_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/epics/12").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_epic", {"epic_id": 12})
    assert not result.is_error
    assert result.data == {"id": 12, "deleted": True}
    assert route.called
```
```python
# tests/mocked/test_tools_epic_comment.py
@pytest.mark.asyncio
@respx.mock
async def test_delete_epic_comment_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/epics/12/comments/8").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_epic_comment", {"epic_id": 12, "comment_id": 8})
    assert not result.is_error
    assert result.data == {"id": 8, "deleted": True}
    assert route.called
```
- [ ] **Step 2 — FAIL.**
- [ ] **Step 3 — Implement.**
```python
# tools/epic.py
    @server.tool(
        name="shortcut_delete_epic",
        description=(
            "Permanently delete an epic. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_epic(ctx: Context, epic_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/epics/{_seg(str(epic_id))}")
        return {"id": epic_id, "deleted": True}
```
```python
# tools/epic_comment.py
    @server.tool(
        name="shortcut_delete_epic_comment",
        description=(
            "Permanently delete a comment on an epic. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_epic_comment(ctx: Context, epic_id: int, comment_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/epics/{_seg(str(epic_id))}/comments/{_seg(str(comment_id))}")
        return {"id": comment_id, "deleted": True}
```
- [ ] **Step 4 — PASS + gates.**
- [ ] **Step 5 — Commit.** `feat(tools): epic + epic_comment delete tools`

### Task 4: iteration + objective deletes

**Files:** `tools/iteration.py`, `tools/objective.py`; matching test files.

- [ ] **Step 1 — Failing tests.**
```python
# tests/mocked/test_tools_iteration.py
@pytest.mark.asyncio
@respx.mock
async def test_delete_iteration_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/iterations/2").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_iteration", {"iteration_id": 2})
    assert not result.is_error
    assert result.data == {"id": 2, "deleted": True}
    assert route.called
```
```python
# tests/mocked/test_tools_objective.py
@pytest.mark.asyncio
@respx.mock
async def test_delete_objective_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/objectives/6").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_objective", {"objective_id": 6})
    assert not result.is_error
    assert result.data == {"id": 6, "deleted": True}
    assert route.called
```
- [ ] **Step 2 — FAIL.**
- [ ] **Step 3 — Implement.**
```python
# tools/iteration.py
    @server.tool(
        name="shortcut_delete_iteration",
        description=(
            "Permanently delete an iteration. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_iteration(ctx: Context, iteration_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/iterations/{_seg(str(iteration_id))}")
        return {"id": iteration_id, "deleted": True}
```
```python
# tools/objective.py
    @server.tool(
        name="shortcut_delete_objective",
        description=(
            "Permanently delete an objective. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_objective(ctx: Context, objective_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/objectives/{_seg(str(objective_id))}")
        return {"id": objective_id, "deleted": True}
```
- [ ] **Step 4 — PASS + gates.**
- [ ] **Step 5 — Commit.** `feat(tools): iteration + objective delete tools`

### Task 5: label + project + file + linked_file deletes

**Files:** `tools/label.py`, `tools/project.py`, `tools/file.py`, `tools/linked_file.py`; matching test files.

- [ ] **Step 1 — Failing tests.**
```python
# tests/mocked/test_tools_label.py
@pytest.mark.asyncio
@respx.mock
async def test_delete_label_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/labels/15").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_label", {"label_id": 15})
    assert not result.is_error
    assert result.data == {"id": 15, "deleted": True}
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_delete_label_surfaces_client_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.delete(f"{BASE}/labels/15").mock(return_value=httpx.Response(404, json={"message": "Not Found"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_label", {"label_id": 15}, raise_on_error=False)
    assert result.is_error
```
```python
# tests/mocked/test_tools_project.py
@pytest.mark.asyncio
@respx.mock
async def test_delete_project_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/projects/21").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_project", {"project_id": 21})
    assert not result.is_error
    assert result.data == {"id": 21, "deleted": True}
    assert route.called
```
```python
# tests/mocked/test_tools_file.py
@pytest.mark.asyncio
@respx.mock
async def test_delete_file_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/files/30").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_file", {"file_id": 30})
    assert not result.is_error
    assert result.data == {"id": 30, "deleted": True}
    assert route.called
```
```python
# tests/mocked/test_tools_linked_file.py
@pytest.mark.asyncio
@respx.mock
async def test_delete_linked_file_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/linked-files/41").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_linked_file", {"linked_file_id": 41})
    assert not result.is_error
    assert result.data == {"id": 41, "deleted": True}
    assert route.called
```
- [ ] **Step 2 — FAIL.**
- [ ] **Step 3 — Implement.**
```python
# tools/label.py
    @server.tool(
        name="shortcut_delete_label",
        description=(
            "Permanently delete a label. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_label(ctx: Context, label_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/labels/{_seg(str(label_id))}")
        return {"id": label_id, "deleted": True}
```
```python
# tools/project.py
    @server.tool(
        name="shortcut_delete_project",
        description=(
            "Permanently delete a project. Irreversible. The Shortcut API rejects this "
            "with a 422 if the project still has stories — move or delete them first. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_project(ctx: Context, project_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/projects/{_seg(str(project_id))}")
        return {"id": project_id, "deleted": True}
```
```python
# tools/file.py
    @server.tool(
        name="shortcut_delete_file",
        description=(
            "Permanently delete an uploaded file. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_file(ctx: Context, file_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/files/{_seg(str(file_id))}")
        return {"id": file_id, "deleted": True}
```
```python
# tools/linked_file.py
    @server.tool(
        name="shortcut_delete_linked_file",
        description=(
            "Permanently delete a linked file. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_linked_file(ctx: Context, linked_file_id: int) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/linked-files/{_seg(str(linked_file_id))}")
        return {"id": linked_file_id, "deleted": True}
```
- [ ] **Step 4 — PASS + gates.** `uv run pytest tests/mocked/ -q && uv run ruff check . && uv run ruff format --check . && uv run ty check`
- [ ] **Step 5 — Commit.** `feat(tools): label/project/file/linked_file delete tools`

---

## Phase 3 — Visibility gate

### Task 6: server-level destructive visibility

**Files:** `tests/test_server.py`

The existing `test_writes_still_absent_without_destructive` (lines ~326–347) runs in `readwrite` + `profile=all` with destructive OFF and asserts no `shortcut_delete*` tools appear — this stays **true and correct** after Phase 1–2 (the `destructive` tag is disabled when `SHORTCUT_ALLOW_DESTRUCTIVE` is unset). Update only its name/docstring to drop the stale "v0.4 scope, no delete tools exist yet" framing, and add a `len(names) == 81` assertion. Then add the destructive-enabled surface test.

- [ ] **Step 1 — Edit the existing test.** Rename `test_writes_still_absent_without_destructive` → `test_deletes_hidden_without_destructive_flag`; replace its docstring with: `"""readwrite + profile=all but ALLOW_DESTRUCTIVE unset: writes visible, all deletes hidden."""`; keep the `delete_tools` assertion and add at the end:
```python
    assert len(names) == 81, f"Expected 81 tools (43 read + 38 write, no destructive), got {len(names)}"
```

- [ ] **Step 2 — Add a config-level gate test** (alongside `test_server_in_readwrite_keeps_writes`):
```python
def test_server_with_destructive_enabled_keeps_destructive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    server = create_server()
    disabled = _disabled_tags(server)
    assert "write" not in disabled
    assert "destructive" not in disabled
```

- [ ] **Step 3 — Add the full destructive surface test:**
```python
@pytest.mark.asyncio
@respx.mock
async def test_destructive_exposes_delete_surface(monkeypatch: pytest.MonkeyPatch) -> None:
    """readwrite + ALLOW_DESTRUCTIVE=true + profile=all exposes all 13 deletes (94 total)."""
    from fastmcp import Client

    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get("https://api.app.shortcut.com/api/v3/member").mock(
        return_value=httpx.Response(200, json={"id": "u1", "name": "tester"})
    )
    server = create_server()
    async with server._lifespan(server), Client(server) as client:
        names = {t.name for t in await client.list_tools()}

    expected_deletes = {
        "shortcut_delete_story",
        "shortcut_bulk_delete_stories",
        "shortcut_delete_story_comment",
        "shortcut_delete_story_task",
        "shortcut_delete_story_link",
        "shortcut_delete_epic",
        "shortcut_delete_epic_comment",
        "shortcut_delete_iteration",
        "shortcut_delete_objective",
        "shortcut_delete_label",
        "shortcut_delete_project",
        "shortcut_delete_file",
        "shortcut_delete_linked_file",
    }
    assert expected_deletes <= names, f"Missing delete tools: {expected_deletes - names}"
    assert "shortcut_delete_group" not in names, "groups have no DELETE endpoint"
    assert {n for n in names if n.startswith("shortcut_delete")} == expected_deletes
    assert len(names) == 94, f"Expected 94 tools (43 read + 38 write + 13 destructive), got {len(names)}"
```

- [ ] **Step 4 — Run, PASS + gates.** `uv run pytest tests/test_server.py -v && uv run ruff check . && uv run ruff format --check . && uv run ty check`
- [ ] **Step 5 — Commit.** `test(server): destructive-tier visibility under SHORTCUT_ALLOW_DESTRUCTIVE`

---

## Phase 4 — Opt-in live harness + docs

### Task 7: opt-in live destructive harness (skip-by-default)

**Files:** `pyproject.toml`, `tests/conftest.py`, `tests/integration/test_live_destructive.py`

> SAFETY: this harness must NEVER run against the nightly read token or any real workspace. It requires a **separate** token env var and an explicit opt-in flag, and skips otherwise. It creates and deletes only its own fixtures.

- [ ] **Step 1 — Add the marker.** In `pyproject.toml` `markers = [...]`, append:
```toml
    "live_write: opt-in live write/destructive tests against an isolated workspace",
```

- [ ] **Step 2 — Add the gated fixture** to `tests/conftest.py`:
```python
@pytest.fixture
def live_write_token() -> str:
    """Isolated write/destructive workspace token. Skips unless explicitly opted in.

    Requires BOTH SHORTCUT_LIVE_WRITE_TESTS=true AND a token in
    SHORTCUT_TEST_WORKSPACE_TOKEN (deliberately NOT SHORTCUT_API_TOKEN, so the
    nightly read token can never be used to mutate or delete data).
    """
    if os.environ.get("SHORTCUT_LIVE_WRITE_TESTS", "").lower() != "true":
        pytest.skip("SHORTCUT_LIVE_WRITE_TESTS != true; skipping live write/destructive test")
    token = os.environ.get("SHORTCUT_TEST_WORKSPACE_TOKEN")
    if not token:
        pytest.skip("SHORTCUT_TEST_WORKSPACE_TOKEN not set; skipping live write/destructive test")
    return token
```

- [ ] **Step 3 — Write the live test.** Create `tests/integration/test_live_destructive.py`:
```python
"""Opt-in live destructive test — disposable fixtures in an ISOLATED workspace.

Skips unless SHORTCUT_LIVE_WRITE_TESTS=true and SHORTCUT_TEST_WORKSPACE_TOKEN is
set (never the nightly read token). Creates its own story, deletes it via the
MCP tool, and asserts the resource is gone. Never runs on the default suite or
the nightly read cron.

Run with:
    SHORTCUT_LIVE_WRITE_TESTS=true SHORTCUT_TEST_WORKSPACE_TOKEN=<token> \\
        uv run pytest tests/integration/test_live_destructive.py -m live_write -v
"""

from __future__ import annotations

import pytest

from shortcut_mcp.clients.shortcut import ShortcutClient
from shortcut_mcp.errors import ShortcutClientError


@pytest.mark.live_write
@pytest.mark.asyncio
async def test_live_delete_story_round_trip(live_write_token: str) -> None:
    async with ShortcutClient(token=live_write_token) as client:
        workflows = await client.get("/workflows")
        assert workflows, "isolated workspace has no workflows"
        state_id = workflows[0]["states"][0]["id"]

        created = await client.post(
            "/stories",
            json={"name": "shortcut-mcp live-destructive fixture (safe to delete)", "workflow_state_id": state_id},
        )
        story_id = created["id"]

        try:
            await client.delete(f"/stories/{story_id}")
        except Exception:
            # Delete failed — make sure we still clean up the fixture, then re-raise.
            with pytest.raises(Exception):  # noqa: B017 - best-effort cleanup
                await client.delete(f"/stories/{story_id}")
            raise

        with pytest.raises(ShortcutClientError):
            await client.get(f"/stories/{story_id}")
```

- [ ] **Step 4 — Verify it SKIPS by default.**
  Run: `uv run pytest tests/integration/test_live_destructive.py -v`
  Expected: 1 skipped (no opt-in flag). Also confirm `uv run pytest -q -m "not live and not live_write"` stays green and the default `uv run pytest -q` does not hit the network.
  Then: `uv run ruff check . && uv run ruff format --check . && uv run ty check`.

- [ ] **Step 5 — Commit.** `test(live): opt-in destructive harness against isolated workspace`

### Task 8: README + CHANGELOG

**Files:** `README.md`, `CHANGELOG.md`

- [ ] **Step 1 — README.** Flip the safety-model table to show the destructive row as shipped: `SHORTCUT_MODE=readwrite` + `SHORTCUT_ALLOW_DESTRUCTIVE=true` → + the 13 destructive tools. List the delete tools and state plainly: deletes are irreversible; `delete_project` requires an empty project; there is **no `delete_group`** (no API endpoint). Document the opt-in live harness env vars (`SHORTCUT_LIVE_WRITE_TESTS`, `SHORTCUT_TEST_WORKSPACE_TOKEN`) and that it must use an isolated workspace.

- [ ] **Step 2 — CHANGELOG.** Under `## [Unreleased]` / `### Added`:
```markdown
- **v0.4 destructive tier — 13 delete tools**, gated by `SHORTCUT_MODE=readwrite`
  **and** `SHORTCUT_ALLOW_DESTRUCTIVE=true` (hidden unless both are set):
  `delete_story`, `bulk_delete_stories`, `delete_story_comment`, `delete_story_task`,
  `delete_story_link`, `delete_epic`, `delete_epic_comment`, `delete_iteration`,
  `delete_objective`, `delete_label`, `delete_project`, `delete_file`, `delete_linked_file`.
  No `delete_group` (no API endpoint).
- **`require_destructive` runtime guard live** on every delete handler (defense-in-depth
  beyond the tag-visibility gate).
- **Opt-in live destructive test harness** (`SHORTCUT_LIVE_WRITE_TESTS` +
  `SHORTCUT_TEST_WORKSPACE_TOKEN`) using disposable fixtures in an isolated workspace;
  never runs on the default suite or the nightly read cron.
```

- [ ] **Step 3 — Full gate.** `uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run ty check`
- [ ] **Step 4 — Commit.** `docs: v0.4 destructive tier`

---

## Done criteria

- `uv run pytest -q` green; ruff + ruff-format + ty clean.
- `readonly` (default) exposes only 43 reads; `readwrite` adds 38 writes (81); `readwrite` + `SHORTCUT_ALLOW_DESTRUCTIVE=true` adds 13 deletes (94).
- Every delete handler calls `require_destructive(ctx)` first and returns `{"id"/"story_ids", "deleted": True}`.
- No `shortcut_delete*` tool is visible unless `destructive_enabled`; no `delete_group` exists.
- Live destructive harness skips by default and only runs against `SHORTCUT_TEST_WORKSPACE_TOKEN` when explicitly opted in.
- Branch `feat/v0.4-destructive-tier` (stacked on `feat/v0.3-write-tier`) ready for a stacked PR.

## Self-review notes (author)

- **Spec coverage:** all 13 destructive tools from § Tool inventory v0.4 mapped to tasks; `delete_group` correctly omitted (§ API quirks "Groups have no DELETE"); comment-reaction DELETE stays in the v0.3 write tier (not re-added here); bulk-delete classified destructive per § Safety model. Live-test isolation matches § Testing "write/destructive live tests are opt-in only … isolated test workspace token."
- **Layering:** the client `delete(json=…)`, `destructive_tags`, `require_destructive`, and its raise/allow unit tests all pre-exist (v0.2/v0.3) — not re-tested here; per-module tests cover path + confirmation shape + one error surface (`delete_label` 404); server tests cover visibility/counts.
- **Counts:** 43 read + 38 write (per `test_readwrite_exposes_write_surface`) + 13 destructive = 94.
