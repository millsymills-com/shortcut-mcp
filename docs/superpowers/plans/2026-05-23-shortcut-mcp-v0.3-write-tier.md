# shortcut-mcp v0.3 Write Tier — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add the write-tier tools (~37) — create/update/archive/reaction/upload across all core resources — gated behind `SHORTCUT_MODE=readwrite`, on top of the v0.2 read surface.

**Architecture:** Extend the existing 17 tool modules' `register()` with write handlers tagged `write_tags(module)` (already disabled in readonly via `server.disable(tags={"write"})`). Add the runtime `require_writes(ctx)` guard to every write handler (defense-in-depth against stale tool-list caches). Two client additions: multipart upload and DELETE-with-body. No `_register_all_tools` change needed (modules already imported).

**Tech Stack:** Python 3.13, FastMCP, httpx, pytest/respx/hypothesis, ruff, ty.

---

## Scope

**In:** client multipart upload + DELETE-with-body; make the `require_writes` runtime gate live; ~37 write tools across the 17 modules; `add_story_labels`/`add_story_owners` read-modify-write helpers; mocked tests per tool (incl. a `mode_denied`/visibility check); README/CHANGELOG.

**Out (later tiers/issues):** destructive deletes (v0.4, issue #4); niche resources (v0.5, #5); CI/VCR/live-write harness (#6/#7/#8); the #10/#11 robustness items.

**Design decisions (locked):**
- **File upload input:** `shortcut_upload_file(path: str)` — the server reads a local filesystem path and uploads it as multipart `file0`. Size cap 50 MB; path must exist and be a file. (stdio MCP server has local FS access; base64 args bloat context.)
- **Array updates:** `shortcut_update_story` arrays (`labels`, `owner_ids`, etc.) **replace** (matches `PUT`). Additive edits use separate `shortcut_add_story_labels` / `shortcut_add_story_owners` tools that read-modify-write (GET story, merge, PUT). Tool descriptions state replace-vs-add loudly.
- **Empty PUT body:** `update_*` handlers tolerate a `None` return from `client.put` (Shortcut sometimes returns empty) by re-GETting or synthesizing `{"id": <id>}`.

## File structure

| File | Action | Responsibility |
|---|---|---|
| `clients/shortcut.py` | modify | add `upload(path, *, file_path)` (multipart) + `delete(path, *, json=None)` |
| `tools/_common.py` | modify | add `put_or_refetch(client, path, body, refetch_path)` helper for empty-PUT handling (optional) |
| `tools/<resource>.py` | modify | add write handlers to each module's `register()` |
| `tests/mocked/test_client_*.py` | modify | multipart + delete-body client tests |
| `tests/mocked/test_tools_*.py` | modify | per-write-tool tests (set `SHORTCUT_MODE=readwrite`) |
| `tests/test_server.py` | modify | assert write tools hidden in readonly, visible in readwrite |
| `CHANGELOG.md`, `README.md` | modify | v0.3 entry; safety-table flips writes to "shipped" |

## Tool inventory (write tier)

| Module | Write tools |
|---|---|
| story | `create_story`, `update_story`, `archive_story`, `unarchive_story`, `add_story_labels`, `add_story_owners`, `bulk_create_stories`, `bulk_update_stories`, `create_story_from_template` |
| story_comment | `create_story_comment`, `update_story_comment`, `add_story_comment_reaction`, `remove_story_comment_reaction` |
| story_task | `create_story_task`, `update_story_task` |
| story_link | `create_story_link`, `update_story_link` |
| epic | `create_epic`, `update_epic`, `archive_epic`, `unarchive_epic` |
| epic_comment | `create_epic_comment`, `create_epic_comment_reply`, `update_epic_comment` |
| iteration | `create_iteration`, `update_iteration` |
| objective | `create_objective`, `update_objective` |
| group | `create_group`, `update_group` |
| label | `create_label`, `update_label` |
| project | `create_project`, `update_project` |
| file | `upload_file`, `update_file` |
| linked_file | `create_linked_file`, `update_linked_file` |

---

## Phase 1 — Foundations

### Task 1: Client multipart upload
**Files:** `clients/shortcut.py`; `tests/mocked/test_client_core.py` (or new `test_client_multipart.py`).

- [ ] **Step 1 — failing test.** With `respx`, mock `POST /files`; call `client.upload("/files", file_path=<tmp file>)`; assert the request `Content-Type` starts with `multipart/form-data` and the body contains the file part; assert the parsed JSON is returned. Also a test that a missing path raises a clear error and an oversized file (> cap) raises.
- [ ] **Step 2 — run, FAIL.**
- [ ] **Step 3 — implement.** Add to `ShortcutClient`:
```python
    async def upload(self, path: str, *, file_path: str, max_bytes: int = 50 * 1024 * 1024) -> Any:
        from pathlib import Path
        _validate_path(path)
        p = Path(file_path)
        if not p.is_file():
            raise ShortcutError(status_code=0, body=f"upload: not a file: {file_path!r}")
        size = p.stat().st_size
        if size > max_bytes:
            raise ShortcutError(status_code=0, body=f"upload: file too large ({size} > {max_bytes} bytes)")
        files = {"file0": (p.name, p.read_bytes(), "application/octet-stream")}
        try:
            # omit the client's default application/json Content-Type so httpx sets the multipart boundary
            resp = await self._client.post(path, files=files, headers={"Content-Type": None})
        except httpx.TimeoutException as exc:
            raise ShortcutTimeoutError(status_code=0, body=str(exc)) from exc
        except httpx.ConnectError as exc:
            raise ShortcutConnectionError(status_code=0, body=str(exc)) from exc
        if resp.status_code >= 400:
            raise _map_status_to_error(resp)
        return resp.json() if resp.content else None
```
(If `headers={"Content-Type": None}` doesn't drop the default cleanly in the installed httpx, build a `request` with the multipart content and explicitly `del request.headers["content-type"]` won't apply; instead pass the multipart via `httpx` and set the client without a global content-type — verify with the test that the boundary header is present. Adjust until the test passes.)
- [ ] **Step 4 — pass + gates.** `uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run ty check`.
- [ ] **Step 5 — commit** `feat(client): multipart upload for POST /files`.

### Task 2: Client DELETE-with-body
**Files:** `clients/shortcut.py`; `tests/mocked/test_client_core.py`.

- [ ] **Step 1 — failing test.** Mock `DELETE /stories/1/comments/2/reactions`; call `client.delete(path, json={"emoji": "👍"})`; assert the request carries the JSON body with `emoji`.
- [ ] **Step 2 — FAIL.**
- [ ] **Step 3 — implement.** Change `delete` to accept an optional body:
```python
    async def delete(self, path: str, *, json: dict[str, Any] | None = None) -> Any:
        return await self._request("DELETE", path, json=json)
```
(`_request`/`_issue` already forward `json`; DELETE stays out of `IDEMPOTENT_METHODS` so it is never retried.)
- [ ] **Step 4 — pass + gates.**
- [ ] **Step 5 — commit** `feat(client): optional JSON body on delete()`.

### Task 3: Write-guard live + visibility test
**Files:** `tests/test_server.py`; `tests/mocked/test_common.py` (guards already exist).

- [ ] **Step 1 — failing tests.** `test_write_tools_hidden_in_readonly`: default mode; after Phase 2 adds `create_story`, assert `shortcut_create_story` NOT in tool list. `test_write_tools_visible_in_readwrite`: `SHORTCUT_MODE=readwrite`; assert `shortcut_create_story` IS present. (These pass once Phase 2 lands `create_story` — order Task 4 before finalizing this; until then, write against an existing read tool to assert readonly hides nothing extra.)
- [ ] **Step 2-5** as usual. The `require_writes`/`require_destructive` unit tests already exist in `test_common.py`; this task adds the server-level visibility assertions. Commit `test(server): write-tier visibility under SHORTCUT_MODE`.

---

## Phase 2 — Story writes (pattern-setter)

### Task 4: story write tools
**Files:** `tools/story.py`; `tests/mocked/test_tools_story.py`.

Establish the **write-handler template**:
```python
from shortcut_mcp.tools._common import get_client, require_writes, write_tags

_WRITE_ANN = {"readOnlyHint": False, "destructiveHint": False}

    @server.tool(name="shortcut_create_story", description="Create a story. Requires SHORTCUT_MODE=readwrite.",
                 tags=write_tags(_MODULE), annotations={**_WRITE_ANN, "idempotentHint": False})
    async def shortcut_create_story(
        ctx: Context, name: str, workflow_state_id: int,
        description: str | None = None, epic_id: int | None = None,
        iteration_id: int | None = None, story_type: str | None = None,
        owner_ids: list[str] | None = None, labels: list[str] | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {"name": name, "workflow_state_id": workflow_state_id}
        for k, v in (("description", description), ("epic_id", epic_id), ("iteration_id", iteration_id),
                     ("story_type", story_type), ("owner_ids", owner_ids)):
            if v is not None:
                body[k] = v
        if labels is not None:
            body["labels"] = [{"name": n} for n in labels]
        return await get_client(ctx).post("/stories", json=body)
```
Rules: every write handler calls `require_writes(ctx)` first; `create_*` → POST, `idempotentHint=False`; `update_*` → PUT, `idempotentHint=True`; build the body from only the provided (non-None) params; labels passed as `{"name": ...}` (auto-create).

Tools to implement (with tests, `SHORTCUT_MODE=readwrite` set in each test):
- `create_story` (above)
- `update_story` (PUT `/stories/{id}`; scalar fields + **replace** arrays; tolerate `None` PUT response → return `{"id": story_id}`); description states arrays REPLACE
- `archive_story` / `unarchive_story` (PUT `{archived: true|false}`)
- `add_story_labels(story_id, labels)` / `add_story_owners(story_id, owner_ids)` — GET story, merge with existing `labels`/`owner_ids`, PUT
- `bulk_create_stories(stories: list[dict])` (POST `/stories/bulk`), `bulk_update_stories(story_ids, ...)` (PUT `/stories/bulk`)
- `create_story_from_template(template_id, name?, ...)` (POST `/stories/from-template`)

- [ ] Steps 1-5 TDD per tool; one mocked test per tool asserting the right method + body shape; commit `feat(tools): story write tools`.

---

## Phase 3 — Remaining write modules (batched)

Apply the Phase 2 write template. Each task: add the write handlers to the module's existing `register()`, one mocked test per tool (set `SHORTCUT_MODE=readwrite`), then gates + commit. All `create_*`=POST, `update_*`=PUT (tolerate empty body), `archive_*`/`unarchive_*`=PUT `{archived}`, reactions use `client.delete(json=...)` for remove.

### Task 5: story_comment + story_task + story_link writes
- story_comment: `create_story_comment(story_id, text)` POST `/stories/{id}/comments`; `update_story_comment(story_id, comment_id, text)` PUT; `add_story_comment_reaction(story_id, comment_id, emoji)` POST `.../reactions`; `remove_story_comment_reaction(story_id, comment_id, emoji)` `client.delete(.../reactions, json={"emoji": emoji})`
- story_task: `create_story_task(story_id, description)` POST; `update_story_task(story_id, task_id, description?, complete?)` PUT
- story_link: `create_story_link(verb, subject_id, object_id)` POST `/story-links`; `update_story_link(story_link_id, verb)` PUT `/story-links/{id}`

### Task 6: epic + epic_comment writes
- epic: `create_epic(name, ...)`, `update_epic(epic_id, ...)`, `archive_epic`/`unarchive_epic` (PUT `{archived}`)
- epic_comment: `create_epic_comment(epic_id, text)` POST; `create_epic_comment_reply(epic_id, comment_id, text)` POST `.../comments/{cid}`; `update_epic_comment(epic_id, comment_id, text)` PUT

### Task 7: iteration + objective + group writes
- iteration: `create_iteration(name, start_date, end_date, ...)` POST; `update_iteration(iteration_id, ...)` PUT
- objective: `create_objective(name, ...)` POST; `update_objective(objective_id, ...)` PUT
- group: `create_group(name, mention_name, ...)` POST; `update_group(group_id, ...)` PUT

### Task 8: label + project + linked_file + file writes
- label: `create_label(name, color?)` POST; `update_label(label_id, ...)` PUT
- project: `create_project(name, team_id?, ...)` POST; `update_project(project_id, ...)` PUT
- linked_file: `create_linked_file(name, url, type, ...)` POST; `update_linked_file(linked_file_id, ...)` PUT
- file: `upload_file(path)` → `client.upload("/files", file_path=path)`; `update_file(file_id, name?, ...)` PUT `/files/{id}`

(Each task: failing tests first, set `SHORTCUT_MODE=readwrite`; gates; commit `feat(tools): <modules> write tools`.)

---

## Phase 4 — Finalize

### Task 9: write-surface assertion + docs
**Files:** `tests/test_server.py`, `README.md`, `CHANGELOG.md`.

- [ ] Add `test_readwrite_exposes_write_surface`: `SHORTCUT_MODE=readwrite` + `SHORTCUT_PROFILE=all`; assert all ~37 write tool names present and that total = 43 read + 37 write. Add `test_readonly_hides_all_writes`: default mode; assert none of the write tool names appear.
- [ ] README: flip the safety-model table — `readwrite` now exposes the write tools (list them); document the upload `path` input and the replace-vs-add story-update semantics. CHANGELOG `[Unreleased]`/`Added` for the write tier.
- [ ] Full gate; commit `docs: v0.3 write tier`.

## Done criteria
- `uv run pytest -q` green; ruff + ruff-format + ty clean.
- Default `readonly` exposes only the 43 reads; `readwrite` adds ~37 writes; every write handler calls `require_writes`.
- Upload reads a local path (size-capped); `update_story` replaces arrays with `add_*` helpers for merge; empty PUT bodies tolerated.
- Branch `feat/v0.3-write-tier` ready for a stacked PR onto `feat/v0.2-read-surface`.
