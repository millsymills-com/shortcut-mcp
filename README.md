# shortcut-mcp

Python FastMCP server for the Shortcut REST API. v0.4 ships a complete read
surface, a write tier, and a destructive tier: **47 read + 39 write + 13
destructive tools across 20 resource modules** (99 tools total). Write tools
require `SHORTCUT_MODE=readwrite`; destructive (delete) tools additionally
require `SHORTCUT_ALLOW_DESTRUCTIVE=true`.

## Installation

```bash
uv tool install git+https://github.com/millsymills-com/shortcut-mcp
```

## Usage

Set `SHORTCUT_API_TOKEN` and run:

```bash
shortcut-mcp
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `SHORTCUT_API_TOKEN` | _(required)_ | Shortcut API token |
| `SHORTCUT_MODE` | `readonly` | `readonly` or `readwrite` |
| `SHORTCUT_ALLOW_DESTRUCTIVE` | `false` | With `readwrite`, expose the 13 destructive delete tools |
| `SHORTCUT_PROFILE` | `core` | Named tool bundle — see [Tool profiles](#tool-profiles--gating) |
| `SHORTCUT_TOOLS` | _(unset)_ | Comma-separated module allowlist; overrides `SHORTCUT_PROFILE` |
| `SHORTCUT_API_BASE_URL` | `https://api.app.shortcut.com/api/v3` | API base URL |
| `SHORTCUT_REQUEST_TIMEOUT` | `30` | Per-request timeout in seconds |
| `SHORTCUT_MAX_RETRIES` | `3` | Total request attempts (initial + retries), not extra retries |

## Token security

`SHORTCUT_API_TOKEN` grants full access to your workspace under your account.
Treat it like a password:

- Read it from the environment only. The server never logs it, and you should
  never commit it or paste it into issues, PRs, or test fixtures.
- A token's permissions match the user who created it. Prefer a service account
  with the least access the integration needs.
- Run with the default `SHORTCUT_MODE=readonly` unless you need writes; keep
  `SHORTCUT_ALLOW_DESTRUCTIVE=false` unless delete tools are required.
- For write/destructive testing, use a separate, disposable workspace token
  (`SHORTCUT_TEST_WORKSPACE_TOKEN`) — never the workspace you care about.

## Rate limits & retries

Shortcut rate-limits the API and returns HTTP 429. The client **does not retry
429s**: it raises `ShortcutRateLimitedError`, carrying the upstream
`Retry-After` value (seconds) when present, so the caller decides whether to
back off. Server errors (5xx) raise `ShortcutServerError` and are likewise
surfaced, not retried.

Only transport-level failures (timeouts, connection errors) are retried, up to
`SHORTCUT_MAX_RETRIES` total attempts with exponential backoff. Lower the value
to fail faster, or raise it for flaky networks.

## Tool profiles & gating

`SHORTCUT_PROFILE` selects a named bundle of modules loaded at startup:

| Profile | Modules included |
|---|---|
| `core` (default) | story, story_comment, story_task, story_link, epic, epic_comment, epic_workflow, iteration, objective, member, workflow, label, search |
| `planning` | core + group, project |
| `files` | core + file, linked_file |
| `all` | all 17 modules (43 read + 38 write + 13 destructive tools at the matching gates) |

`SHORTCUT_TOOLS` accepts a comma-separated list of module names and **overrides**
the profile entirely. Unknown module names are rejected at startup.

```bash
# Load only story and search tools
SHORTCUT_TOOLS=story,search shortcut-mcp

# Load the planning bundle
SHORTCUT_PROFILE=planning shortcut-mcp
```

## Safety model

| `SHORTCUT_MODE` | `SHORTCUT_ALLOW_DESTRUCTIVE` | Tools exposed |
|---|---|---|
| `readonly` (default) | _(ignored)_ | 43 read tools only |
| `readwrite` | `false` | 43 read + 38 write tools (81 total) |
| `readwrite` | `true` | 43 read + 38 write + 13 destructive tools (94 total) |

Write tools are hidden entirely in readonly mode — they do not appear in
`list_tools()` output and cannot be called. Setting `SHORTCUT_MODE=readwrite`
is required to expose them. Destructive tools require **both**
`SHORTCUT_MODE=readwrite` and `SHORTCUT_ALLOW_DESTRUCTIVE=true`; with either gate
unset they stay hidden. Each delete handler also calls a runtime guard that
raises `mode_denied` if reached without both gates.

## Tool catalog

### Read tools (47)

`list_*` tools return a shaped envelope `{items: [...], truncated: bool, total?: int}`
and accept a `limit` parameter (default 50; search tools default 25). `get_*`
tools return the full API object.

#### story (2 tools)

- `shortcut_get_story` — Fetch a story by numeric ID.
- `shortcut_list_story_history` — List change history for a story (most recent first).

#### story_comment (2 tools)

- `shortcut_list_story_comments` — List comments on a story (summary rows).
- `shortcut_get_story_comment` — Fetch one story comment (full object).

#### story_task (1 tool)

- `shortcut_get_story_task` — Fetch one task on a story (full object).

#### story_link (1 tool)

- `shortcut_get_story_link` — Fetch one story link by ID (full object).

#### epic (3 tools)

- `shortcut_list_epics` — List all epics (summary rows).
- `shortcut_get_epic` — Fetch one epic by ID (full object).
- `shortcut_list_epic_stories` — List the stories in an epic (summary rows).

#### epic_comment (2 tools)

- `shortcut_list_epic_comments` — List comments on an epic (summary rows).
- `shortcut_get_epic_comment` — Fetch one epic comment (full object).

#### epic_workflow (1 tool)

- `shortcut_get_epic_workflow` — Get the epic workflow (epic states).

#### iteration (3 tools)

- `shortcut_list_iterations` — List all iterations (summary rows).
- `shortcut_get_iteration` — Fetch one iteration by ID (full object).
- `shortcut_list_iteration_stories` — List the stories in an iteration (summary rows).

#### objective (3 tools)

- `shortcut_list_objectives` — List all objectives (summary rows).
- `shortcut_get_objective` — Fetch one objective by ID (full object).
- `shortcut_list_objective_epics` — List the epics under an objective (summary rows).

#### member (3 tools)

- `shortcut_list_members` — List all members (summary rows).
- `shortcut_get_member` — Fetch one member by UUID (full object).
- `shortcut_get_current_member` — Fetch the authenticated member (full object).

#### group (3 tools)

- `shortcut_list_groups` — List all groups/teams (summary rows).
- `shortcut_get_group` — Fetch one group by UUID (full object).
- `shortcut_list_group_stories` — List the stories owned by a group (summary rows).

#### workflow (2 tools)

- `shortcut_list_workflows` — List all workflows (summary rows).
- `shortcut_get_workflow` — Fetch one workflow by ID (full object).

#### label (4 tools)

- `shortcut_list_labels` — List all labels (summary rows).
- `shortcut_get_label` — Fetch one label by ID (full object).
- `shortcut_list_label_stories` — List the stories with a label (summary rows).
- `shortcut_list_label_epics` — List the epics with a label (summary rows).

#### project (3 tools)

- `shortcut_list_projects` — List all projects (summary rows).
- `shortcut_get_project` — Fetch one project by ID (full object).
- `shortcut_list_project_stories` — List the stories in a project (summary rows).

#### file (2 tools)

- `shortcut_list_files` — List all uploaded files (summary rows).
- `shortcut_get_file` — Fetch one uploaded file by ID (full object).

#### linked_file (2 tools)

- `shortcut_list_linked_files` — List all linked files (summary rows).
- `shortcut_get_linked_file` — Fetch one linked file by ID (full object).

#### repository (2 tools)

- `shortcut_list_repositories` — List all VCS repositories (summary rows).
- `shortcut_get_repository` — Fetch one VCS repository by ID (full object).

#### external_link (1 tool)

- `shortcut_list_external_link_stories` — List the stories referencing an external link URL (summary rows).

#### key_result (1 tool)

- `shortcut_get_key_result` — Fetch one objective key-result by ID (full object).

#### search (6 tools)

- `shortcut_search_stories` — Search stories with Shortcut query syntax (e.g. `state:done owner:me`).
- `shortcut_search_epics` — Search epics with Shortcut query syntax.
- `shortcut_search_iterations` — Search iterations with Shortcut query syntax.
- `shortcut_search_objectives` — Search objectives with Shortcut query syntax.
- `shortcut_search` — Global multi-entity search; returns `{stories: {items, truncated}, epics: {items, truncated}}`.
- `shortcut_query_stories` — Search stories by structured filter (POST query; read-only despite POST).

### Write tools (39)

Require `SHORTCUT_MODE=readwrite`. Hidden entirely in readonly mode.

Two behaviors to be aware of:

- **`shortcut_upload_file(path)`** reads **any** filesystem path readable by the
  server process and uploads its bytes to Shortcut. Treat the path as a trust
  boundary: do not expose this server to untrusted prompts when sensitive files
  (keys, credentials) are on disk. Uploads are capped at 50 MB.
- **`shortcut_update_story`** REPLACES `labels` and `owner_ids` arrays — it
  does not append. Use `shortcut_add_story_labels` / `shortcut_add_story_owners`
  to add entries without clobbering the existing values.

#### story (9 tools)

- `shortcut_create_story` — Create a new story.
- `shortcut_update_story` — Update story fields (replaces `labels`/`owner_ids`).
- `shortcut_archive_story` — Archive a story.
- `shortcut_unarchive_story` — Unarchive a story.
- `shortcut_add_story_labels` — Add labels to a story (read-modify-write; safe append).
- `shortcut_add_story_owners` — Add owners to a story (read-modify-write; safe append).
- `shortcut_bulk_create_stories` — Create multiple stories in one request.
- `shortcut_bulk_update_stories` — Update multiple stories by ID list.
- `shortcut_create_story_from_template` — Create a story from a saved template.

#### story_comment (4 tools)

- `shortcut_create_story_comment` — Add a comment to a story.
- `shortcut_update_story_comment` — Edit an existing story comment.
- `shortcut_add_story_comment_reaction` — Add an emoji reaction to a story comment.
- `shortcut_remove_story_comment_reaction` — Remove an emoji reaction from a story comment.

#### story_task (2 tools)

- `shortcut_create_story_task` — Add a task (checklist item) to a story.
- `shortcut_update_story_task` — Update a story task (description, completion state).

#### story_link (2 tools)

- `shortcut_create_story_link` — Create a relationship link between two stories.
- `shortcut_update_story_link` — Update a story link's verb/direction.

#### epic (4 tools)

- `shortcut_create_epic` — Create a new epic.
- `shortcut_update_epic` — Update epic fields.
- `shortcut_archive_epic` — Archive an epic.
- `shortcut_unarchive_epic` — Unarchive an epic.

#### epic_comment (3 tools)

- `shortcut_create_epic_comment` — Add a comment to an epic.
- `shortcut_create_epic_comment_reply` — Reply to an existing epic comment thread.
- `shortcut_update_epic_comment` — Edit an existing epic comment.

#### iteration (2 tools)

- `shortcut_create_iteration` — Create a new iteration.
- `shortcut_update_iteration` — Update an iteration's fields.

#### objective (2 tools)

- `shortcut_create_objective` — Create a new objective.
- `shortcut_update_objective` — Update an objective's fields.

#### group (2 tools)

- `shortcut_create_group` — Create a new group/team.
- `shortcut_update_group` — Update a group's fields.

#### label (2 tools)

- `shortcut_create_label` — Create a new label (labels auto-create by name when
  posted — no pre-creation step needed in most flows).
- `shortcut_update_label` — Update a label's name or color.

#### project (2 tools)

- `shortcut_create_project` — Create a new project.
- `shortcut_update_project` — Update a project's fields.

#### file (2 tools)

- `shortcut_upload_file` — Upload a file from a local path (server-side read).
- `shortcut_update_file` — Update an uploaded file's metadata.

#### linked_file (2 tools)

- `shortcut_create_linked_file` — Create a linked file (external URL reference).
- `shortcut_update_linked_file` — Update a linked file's metadata.

#### key_result (1 tool)

- `shortcut_update_key_result` — Update an objective key-result's name or observed/initial/target value.

### Destructive tools (13)

Require **both** `SHORTCUT_MODE=readwrite` and `SHORTCUT_ALLOW_DESTRUCTIVE=true`.
Hidden unless both are set. Every delete is **irreversible** and returns a
structured confirmation (`{"id": <id>, "deleted": true}`).

- `shortcut_delete_story` — Delete a story.
- `shortcut_bulk_delete_stories` — Delete multiple stories in one request.
- `shortcut_delete_story_comment` — Delete a comment on a story.
- `shortcut_delete_story_task` — Delete a task on a story.
- `shortcut_delete_story_link` — Delete a story link.
- `shortcut_delete_epic` — Delete an epic.
- `shortcut_delete_epic_comment` — Delete a comment on an epic.
- `shortcut_delete_iteration` — Delete an iteration.
- `shortcut_delete_objective` — Delete an objective.
- `shortcut_delete_label` — Delete a label.
- `shortcut_delete_project` — Delete a project (the API returns `422` if the
  project still has stories — move or delete them first).
- `shortcut_delete_file` — Delete an uploaded file.
- `shortcut_delete_linked_file` — Delete a linked file.

There is **no `delete_group`** — the Shortcut API exposes no `DELETE /groups/{id}`
endpoint.

## Testing destructive tools against a live workspace

The default test suite is fully mocked and never touches the network. The
destructive delete path also has an opt-in live test that runs only against an
**isolated, disposable workspace** — never the workspace behind your everyday
`SHORTCUT_API_TOKEN`. It creates its own story, deletes it, and confirms it is
gone. It skips unless **both** of these are set:

| Variable | Purpose |
|---|---|
| `SHORTCUT_LIVE_WRITE_TESTS=true` | Opt-in flag; absent → the test skips |
| `SHORTCUT_TEST_WORKSPACE_TOKEN` | Token for the isolated workspace (deliberately not `SHORTCUT_API_TOKEN`) |

```bash
SHORTCUT_LIVE_WRITE_TESTS=true SHORTCUT_TEST_WORKSPACE_TOKEN=<token> \
    uv run pytest tests/integration/test_live_destructive.py -m live_write -v
```
