# shortcut-mcp Full-Coverage Roadmap — Design

**Date:** 2026-05-23
**Status:** Draft (pending review)
**Repo:** `millsymills-com/shortcut-mcp`
**Supersedes scope of:** the v0.1 dry-run design (`shortcut-test/docs/superpowers/specs/2026-05-22-shortcut-mcp-dry-run-design.md`). The v0.1 architecture stands; this extends it.

## Goal

Take `shortcut-mcp` from its v0.1 tracer state (one read tool, `shortcut_get_story`) to **full CRUD coverage of the core Shortcut REST v3 surface (~92 tools across 17 resource modules)**, shipped as a **public, source-installable, community-grade** FastMCP server.

Most of the work is additive (new `tools/<resource>.py` modules + tests + docs), but **v0.2 deliberately changes the shared scaffolding once**: the client gains multipart upload, DELETE-with-body, and `next`-cursor pagination; config/server gain `SHORTCUT_TOOLS` + tool-profile gating and a shared write/destructive guard helper. After that v0.2 pass, every later tool is a thin additive wrapper that inherits output schemas, annotations, response shaping, pagination, and the guard. The non-additive client/config/server changes are called out explicitly in **§ Client & server changes (v0.2)**.

## Ground truth

The Shortcut v3 API exposes **144 operations across 86 paths** (verified against `shortcut.swagger.json`, retrieved 2026-05-23). This roadmap covers the **core** subset in full and defers a **niche** subset to an optional final milestone.

**Core (in scope, full CRUD):** stories (+ bulk, history, from-template), story comments (+ comment reactions), story tasks, story links, epics, epic comments, epic-workflow, iterations, objectives, members, groups, workflows, labels, projects, files, linked-files, search.

**Niche (deferred to v0.5, only if true 1:1 is wanted):** categories, custom-fields, entity-templates, documents, repositories, external-links, key-results, health (epic/objective), document-search, story sub-tasks, comment Slack-unlinking.

**Permanently out of scope:** `milestones/*` (legacy alias of objectives — use objectives), `integrations/webhook/*` (webhook management is a distinct feature), OAuth (token-only), multi-workspace/multi-token, PyPI publishing, GraphQL.

## Approach (chosen): horizontal safety tiers

Ship by safety tier across all core resources. Each tier is a releasable minor version with a clean, marketable narrative, and maps directly onto the existing tag-gate architecture (`read` / `write` / `destructive`).

| Version | Tier | Tools | Theme |
|---|---|---|---|
| **v0.2** | read | ~43 | Complete read surface + cross-cutting quality bar + community deliverables |
| **v0.3** | write | ~36 | create / update / archive / reply / upload / reaction across all core resources |
| **v0.4** | destructive | ~13 | delete + bulk-delete, gated behind `SHORTCUT_ALLOW_DESTRUCTIVE` |
| **v0.5** | niche (optional) | ~30 | the niche resources + workspace feature toggles — true 1:1 |

**Rejected alternatives:**
- **Vertical resource clusters** (full CRUD per resource, one cluster per release): delivers complete per-resource workflows sooner but every release mixes read/write/destructive (muddier safety story for adopters) and repeatedly revisits the cross-cutting concerns.
- **Big-bang** (~92 tools in one plan): abandons the tracer-bullet discipline the dry-run proved; produces an unreviewable plan.

Why horizontal wins here: read-only is safe to install anywhere, so the community-adoption path is lowest-risk; the cross-cutting quality bar is set once in v0.2 and inherited; and "read-only → writes → full CRUD" is the clearest possible release story.

## Architecture

The v0.1 split is unchanged and proven:

- **`clients/shortcut.py`** (built) — async `httpx` wrapper, generic `get`/`post`/`put`/`delete`, `_seg()` path encoding, URL/prefix validation, typed-error taxonomy, narrow `tenacity` retry (GET/HEAD timeout/connection only; never 429, never writes), `None` for 204.
- **`tools/<resource>.py`** — one module per resource group, each exporting `register(server)`. FastMCP introspects annotations at runtime, so `Context`/`FastMCP` imports stay un-`TYPE_CHECKING`-guarded (per-file ruff `TC001`/`TC002` ignore already in place).
- **`server.py`** (built) — `_register_all_tools` calls every module's `register`; visibility gated post-registration via `server.disable(tags=…)`. Lifespan-managed `ServerContext` (config + client). Auth-failure kill switch disables the `shortcut` tag.
- **`config.py`** (built) — frozen `BaseSettings`, `SecretStr` token, `writes_enabled`/`destructive_enabled`/`authenticated` properties.

Tool naming convention: `shortcut_<verb>_<resource>` (e.g. `shortcut_create_story`, `shortcut_list_epic_comments`). `_register_all_tools` grows one import + call per new module.

### Five cross-cutting additions (all land in v0.2)

1. **Tool annotations.** Every tool declares MCP behavioral hints (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) alongside the existing tags, so clients reason about safety without invoking. Reads: `readOnlyHint=true`. Writes: `idempotentHint=true` for PUT-based updates, `false` for POST creates. Deletes: `destructiveHint=true`.

2. **Output schemas / structured content.** Tools declare typed return shapes (FastMCP `output_schema` / typed return annotations) so MCP clients receive structured results rather than opaque blobs. This is a deliberate departure from the eval prototype's "no models" rule, which applied only to throwaway code; declared I/O is a quality requirement for a shipped server. Request bodies stay as explicit typed handler parameters (no Pydantic request models needed — FastMCP derives the input schema from the signature).

3. **Response shaping + truncation (`tools/_common.py`).** Shortcut story/epic objects are large; raw list responses overflow the agent context window. The existing `shape_story` placeholder is fleshed out into per-resource summary shapers: `list_*`/`search_*` return trimmed summary rows by default (id, name, key state/dates, owner/epic refs); `get_*` returns the full object; a `detail: bool = False` parameter on list tools opts into full rows. **Every list/search tool also takes a `limit` (default e.g. 50) and returns `{items, truncated, total?}`** so an unbounded non-paginated array (files, labels, project stories, comments) can never dump thousands of rows. This is the single biggest token-cost lever.

4. **Pagination helper (`clients/shortcut.py`).** Two distinct shapes:
   - `GET /search/{stories,epics,iterations,objectives}` and `GET /epics/paginated` return a `{data, next, total}` envelope. A `paginate()` helper follows `next` up to a `max_pages` guard (default small, e.g. 5) bounded by the tool's `limit`. The documented `next` value is a **path + query string**, which collides with the client's "query never in the path" invariant — so the helper parses `next` into `(path, params)`, asserts it is relative to `/api/v3` (rejecting any absolute URL, same as `_seg`'s prefix rule), and re-issues via `params=`.
   - `GET /search` (global) returns a nested `SearchResults` object (per-type envelopes), **not** `{data, next, total}`. It gets its own non-paginated shaper; the `paginate()` helper is never run over it.

5. **Tool gating: `SHORTCUT_TOOLS` allowlist + profiles (config + server change).** Not additive — a new frozen `config.py` field plus new visibility logic in `server.py` (which today only checks `write`/`destructive`/`shortcut`). Each module registers a per-module tag (`mod:<resource>`); after registration the server disables modules outside the selected set. `SHORTCUT_TOOLS` is an explicit comma-separated module allowlist; `SHORTCUT_PROFILE` selects a named bundle — `core` (stories, epics, iterations, objectives, members, workflows, labels — the default, ~25 tools), `planning` (+ groups, projects), `files`, or `all`. Default `core` keeps the readonly surface well under the ~43 full-read count, addressing tool-selection overload while leaving full coverage one env var away. Composition with mode/destructive/auth gates is unit-tested.

6. **Shared mode-guard helper (`tools/_common.py`), landed in v0.2.** A `require_writes(ctx)` / `require_destructive(ctx)` helper raises `ToolError(code="mode_denied", message=…)` by reading `ctx.lifespan_context.config`. It ships in v0.2 (with the existing scaffolded regression test made live against a throwaway write tool) so that when real write tools arrive in v0.3 the enforcement pattern already exists and every handler just calls the helper — no copy-pasted gate logic.

### Client & server changes (v0.2) — the non-additive parts

These touch existing scaffolding and must land before the tools that depend on them:

- **`ShortcutClient.post` multipart support** — `POST /files` is `multipart/form-data` with a required `file0` part; the current `post()` always sends JSON with a global `Content-Type: application/json`. Add a multipart path that omits the JSON content type, accepts a bounded byte/stream input (with a size cap) + filename, and is tested against the OpenAPI form fields. (Required by `upload_file`, v0.3.)
- **`ShortcutClient.delete` body support** — `DELETE …/comments/{cid}/reactions` requires a `CreateOrDeleteStoryReaction` body (`emoji` required); current `delete(path)` sends no body. Add `delete(path, *, json=None)` with a test proving the emoji body is transmitted. (Required by `remove_story_comment_reaction`, v0.3.)
- **`next`-cursor pagination parsing** — see cross-cutting addition #4.
- **`SHORTCUT_TOOLS` / `SHORTCUT_PROFILE` config field + module-tag visibility logic** — see addition #5.
- **`require_writes` / `require_destructive` guard helper** — see addition #6.

## Safety model

Two orthogonal env gates, two enforcement layers — unchanged from v0.1, now exercised:

| `SHORTCUT_MODE` | `SHORTCUT_ALLOW_DESTRUCTIVE` | Tools exposed |
|---|---|---|
| `readonly` (default) | n/a | reads only (~43) |
| `readwrite` | `false` (default) | + writes (~36) |
| `readwrite` | `true` | + destructive (~13) |

**Tier classification by operation semantics (not HTTP method) — with explicit exceptions:**
- **read** — any operation with no side effects. This includes the **query POST** `POST /stories/search` (`query_stories`), which is read-only despite its method. Method alone never decides the tier.
- **write** — create or mutate existing data. Includes: **archive** (`PUT {archived: true}` — reversible, no archive endpoint; exposed as named `archive_*`/`unarchive_*` helpers, see below), **comment-reaction add/remove** (`POST`/`DELETE …/reactions` — trivially reversible), and **file upload** (`POST /files`, multipart).
- **destructive** — irreversible data loss: every `DELETE` of a substantive entity **plus `DELETE /stories/bulk`**. Comment-reaction `DELETE` is **excluded** (reversible → write).
- **workspace feature toggles** — `PUT /iterations/{enable,disable}` and `PUT /entity-templates/{enable,disable}` change a workspace-wide feature flag, not a resource. They are **not** part of "core iteration CRUD"; classified as write-tier admin and **deferred to v0.5** with a warning annotation (workspace-wide blast radius, rarely scripted).

Named **archive helpers** (`archive_story`/`unarchive_story`, `archive_epic`/`unarchive_epic`) wrap `PUT` with only the `archived` field — more discoverable and safer than asking an agent to hand-craft an `update` payload. They live in the write tier (v0.3).

**Visibility gate:** `server.disable(tags={"write"|"destructive"})` per config; auth failure disables `tags={"shortcut"}`; module gating per `SHORTCUT_TOOLS`/`SHORTCUT_PROFILE`.
**Runtime gate (defense-in-depth):** the shared `require_writes`/`require_destructive` helper (cross-cutting addition #6) lands in **v0.2** with its regression test made live, so every write/destructive handler in v0.3/v0.4 simply calls it — no per-handler gate logic.

## API quirks to encode (discovered from the swagger + carried from the CLI eval)

These become property-test invariants and handler-level handling:

- **No list endpoints for embedded children.** Story **tasks**, **comment reactions**, and **story links** have no `GET …/tasks`, `…/reactions`, or `…/links` list endpoint — they arrive embedded in the parent story/comment. Tools expose `get`/`create`/`update`/`delete` on the child by id; "list" is "read the parent." (Story-level reactions do **not** exist at all — only comment reactions.)
- **Groups have no `DELETE`.** No `shortcut_delete_group` tool; groups get create/update but not destructive.
- **`PUT /stories/{id}` replaces arrays, does not append.** Expose replace vs. add explicitly in `update_story` (mirrors the CLI's `--set-*`/`--add-*`; add does client-side read-modify-write). Silent replace corrupts data.
- **`PUT /stories/{id}` may return an empty body.** Handler synthesizes `{"id": story_id}` (or re-GETs) when `client.put` returns `None`. (Carryover from `shortcut-test` `cli.py:286`.)
- **`/search/*` returns `{data, next, total}`**, not a bare list. Two search styles exist: `GET /search/{entity}` (cursor-paginated) and `POST /stories/search` (body query). v0.2 uses the `GET /search/*` family.
- **`/members` nests fields under `profile.*`** (`profile.mention_name`, `profile.name`), not top-level.
- **Labels auto-create from `{"name": "..."}`** on story/epic create — no pre-creation step.
- **`shortcut_max_retries` counts total attempts** (`tenacity.stop_after_attempt`), not extra retries. Documented at the field; consider a clarifying rename in v0.2.

## Tool inventory (the implementation contract)

Authoritative mapping of every core endpoint → tool → tier. Tools omitted where the API has no endpoint (noted above).

### v0.2 — read (~43)

| Module | Tools | Endpoints |
|---|---|---|
| story | `get_story`, `list_story_history` | `GET /stories/{id}`, `GET /stories/{id}/history` |
| story_comment | `list_story_comments`, `get_story_comment` | `GET /stories/{id}/comments`, `GET …/comments/{cid}` |
| story_task | `get_story_task` | `GET /stories/{id}/tasks/{tid}` |
| story_link | `get_story_link` | `GET /story-links/{id}` |
| epic | `list_epics`, `get_epic`, `list_epic_stories` | `GET /epics` (+ `/epics/paginated`), `GET /epics/{id}`, `GET /epics/{id}/stories` |
| epic_comment | `list_epic_comments`, `get_epic_comment` | `GET /epics/{id}/comments`, `GET …/comments/{cid}` |
| epic_workflow | `get_epic_workflow` | `GET /epic-workflow` |
| iteration | `list_iterations`, `get_iteration`, `list_iteration_stories` | `GET /iterations`, `GET /iterations/{id}`, `GET /iterations/{id}/stories` |
| objective | `list_objectives`, `get_objective`, `list_objective_epics` | `GET /objectives`, `GET /objectives/{id}`, `GET /objectives/{id}/epics` |
| member | `list_members`, `get_member`, `get_current_member` | `GET /members`, `GET /members/{id}`, `GET /member` |
| group | `list_groups`, `get_group`, `list_group_stories` | `GET /groups`, `GET /groups/{id}`, `GET /groups/{id}/stories` |
| workflow | `list_workflows`, `get_workflow` | `GET /workflows`, `GET /workflows/{id}` |
| label | `list_labels`, `get_label`, `list_label_stories`, `list_label_epics` | `GET /labels`, `GET /labels/{id}`, `GET /labels/{id}/stories`, `GET /labels/{id}/epics` |
| project | `list_projects`, `get_project`, `list_project_stories` | `GET /projects`, `GET /projects/{id}`, `GET /projects/{id}/stories` |
| file | `list_files`, `get_file` | `GET /files`, `GET /files/{id}` |
| linked_file | `list_linked_files`, `get_linked_file` | `GET /linked-files`, `GET /linked-files/{id}` |
| search | `search`, `search_stories`, `search_epics`, `search_iterations`, `search_objectives`, `query_stories` | `GET /search`, `GET /search/{stories,epics,iterations,objectives}`, `POST /stories/search` (read-only query) |

### v0.3 — write (~36)

| Module | Tools |
|---|---|
| story | `create_story`, `update_story`, `archive_story`, `unarchive_story`, `bulk_create_stories`, `bulk_update_stories`, `create_story_from_template` |
| story_comment | `create_story_comment`, `update_story_comment`, `add_story_comment_reaction`, `remove_story_comment_reaction` (sends `emoji` body via DELETE) |
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

### v0.4 — destructive (~13)

`delete_story`, `bulk_delete_stories`, `delete_story_comment`, `delete_story_task`, `delete_story_link`, `delete_epic`, `delete_epic_comment`, `delete_iteration`, `delete_objective`, `delete_label`, `delete_project`, `delete_file`, `delete_linked_file`. (No `delete_group` — endpoint absent.)

### v0.5 — niche (optional, ~30)

categories CRUD + 2 association lists; custom-fields list/get/update/delete (no create); entity-templates CRUD + enable/disable; documents CRUD + epic link/unlink + tiptap-load + search/documents; repositories list/get; external-link stories; key-results get/update; epic & objective health get/create/history + `PUT /health/{id}`; story sub-tasks; iteration enable/disable. (Some v0.5 reads — custom-fields, repositories — may be pulled forward if v0.3 writes need them as references; flagged, not committed.)

## Testing strategy

Markers (`mocked`/`live`/`smoke`/`slow`) per v0.1; tightened for shipping. Tests are layered so each concern is covered **once** at the right level — the ~92 tools are thin wrappers and must not each re-test shared client behavior.

- **Client layer owns the error matrix.** The exhaustive typed-error branches (auth / client / rate-limit / server / timeout / connection) + retry policy (GET/HEAD-only, never-429, never-write) + multipart + DELETE-with-body + `next`-cursor parsing are tested **exhaustively in `tests/mocked/test_client_*.py`**, not repeated per tool.
- **Tool-module tests are focused (`respx`).** Per module: correct path + body construction, summary-shaping/truncation, pagination wiring, and gate behavior (`mode_denied` when the mode is flipped after registration). One representative error case per module to prove the handler surfaces client errors — not the whole matrix again.
- **Property tests (`hypothesis`)** encoding the quirks as invariants: `/search/*` `{data,next,total}` envelope and `/search` nested shape; `/members` `profile.*` nesting; `PUT` empty-body → synthetic response; arrays replace-not-append on `update_story`; pagination terminates and respects `max_pages`; summary shapers never raise on missing optional fields.
- **Contract tests (VCR cassettes, `pytest-recording`) — selective.** Record representative real-shape responses for the quirky/large payloads (story, epic, search envelope, members `profile.*`, paginated epics) — **not** every thin wrapper. Rig lands in v0.2.
- **Live integration smoke, split by safety:**
  - **Read smoke** runs on the nightly cron against the standard `SHORTCUT_API_TOKEN`; skips when absent; honors `SHORTCUT_SMOKE_STORY_ID` / `tracer-bullet` fallback.
  - **Write/destructive live tests are opt-in only** behind `SHORTCUT_LIVE_WRITE_TESTS=true`, run against an **isolated test workspace token** (never the nightly read token), create their own disposable fixtures, and clean them up. Destructive live tests never run on the default nightly cron. This prevents the live suite from mutating or deleting real workspace data.
- **CI gates:** `ruff check`, `ty check`, `bandit`, `pip-audit`, `pytest` on **Python 3.13** (matches `pyproject` `requires-python >=3.13`; bump to a 3.12+3.13 matrix only if metadata is lowered first); CodeQL; coverage floor (e.g. 90% on `tools/` + `clients/`); release-install smoke (`uv tool install` from a clean checkout boots the server).

## Community / shippability deliverables (v0.2)

- Make repo **public**.
- **README** with an auto-generated **tool catalog** (name, tier, one-line description), safety-model table, `SHORTCUT_TOOLS`/`SHORTCUT_PROFILE` usage, limitations, and a **token-security section** (token creation, least-privilege/workspace blast radius per mode, rotation, `.env` handling) and **rate-limit guidance** (429 behavior; `retry_after` is surfaced in the tool error so agents can back off).
- **Discoverability:** submit to the **MCP registry** with server metadata/manifest; provide **client config examples beyond Claude Code** (Claude Desktop, Cursor, Windsurf, generic stdio). State the **no-PyPI tradeoff** explicitly in the README (source install only).
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, issue + PR templates, `CODEOWNERS`.
- `CHANGELOG.md` (Keep-a-Changelog) + semver GitHub Releases per minor version. **Single-source versioning:** `__version__` reads from installed package metadata; a release checklist keeps `pyproject`, `CHANGELOG`, and the git tag from drifting.
- `pre-commit` config; `dependabot.yml` (pip + actions, 7-day cooldown, grouped).
- Install path: `uv tool install git+https://github.com/millsymills-com/shortcut-mcp.git` (no PyPI, per decision).
- Badges: CI, CodeQL, license, Python version.

## Dogfooding into Shortcut

Mirror Shortcut's own hierarchy so the roadmap dogfoods objectives + epics + iterations, not just stories:

- One **Objective**: "Full Shortcut API coverage (1:1)".
- One **Epic per version**: v0.2 read, v0.3 write, v0.4 destructive, v0.5 niche — each linked to the objective.
- **Stories per tool-batch**, grouped by resource module (~3–6 stories/epic), each labeled `area:tools`/`area:client`/`area:ci`/`area:docs` + `type:feature`/`type:test`/`type:release`.

Backlog is **proposed in full, confirmed with the user, then created** via the `/story` confirm-before-write flow or a batch seed script (per the dry-run). No writes to Shortcut before confirmation.

## Prerequisites & sequencing

- **Reconcile diverged `main` carefully — do not blind-reset.** Local `main` is ahead 9 / behind 1 of `origin/main` (the dry-run squash-merged the 9 tracer commits into one). Procedure: (1) tag a backup ref `git branch backup/local-main-2026-05-23`; (2) confirm the origin squash actually contains all 9 commits' content (`git diff origin/main main -- src tests` should be empty); (3) preserve untracked docs (this spec is untracked — a reset won't delete it, but stash/copy anything in-flight first); (4) only then `git switch main && git reset --hard origin/main`; (5) branch per tier (`feat/v0.2-read-surface`, …). No work on `main`.
- **Org/repo secret** `SHORTCUT_API_TOKEN` in Actions for the nightly live cron (operator task; CI mocked tests pass without it).
- Each tier ships on its own branch → PR → squash-merge → tagged release.

## Open decisions (flagged; default = my recommendation)

1. **Structured output + response shaping (§ Architecture 2–3)** — recommend yes. Flip to raw passthrough if undesired.
2. **VCR cassette rig in v0.2 (§ Testing)** — recommend yes; it costs ~1 iteration. Defer to later if budget is tight.
3. **Dogfood hierarchy: objective → epic-per-version → stories (§ Dogfooding)** — recommend yes; alternative is a flat epic-per-version with no objective.
4. **Niche v0.5** — recommend building it (true 1:1) once core ships; alternative is to stop at v0.4 full-core-CRUD and treat niche as on-demand.
5. **Default tool profile** — recommend `SHORTCUT_PROFILE=core` (~25 tools) as the out-of-box default to limit tool-selection overload, with `all` one env var away. Alternative: default `all` (every registered tool visible) for zero-config full coverage.

## Appendix: full operation count

144 operations / 86 paths total. Core covered by v0.2–v0.4 ≈ 92 tools. Niche + workspace toggles (v0.5) ≈ 30. Excluded (milestones legacy alias, webhook integrations) ≈ remainder. Tool count and operation count differ because embedded-child resources (tasks, links, reactions) have no list endpoints (fewer tools) while a few endpoints expand into multiple ergonomic tools (archive/unarchive wrap one `PUT`; `query_stories` is a read despite POST).
