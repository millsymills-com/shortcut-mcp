# shortcut-mcp

Python FastMCP server for the Shortcut REST API. v0.5 ships a complete read
surface, a write tier, and a destructive tier: **65 read + 51 write + 21
destructive tools across 26 resource modules** (137 tools total). Write tools
require `SHORTCUT_MODE=readwrite`; destructive tools (deletes and workspace-wide
feature toggles) additionally require `SHORTCUT_ALLOW_DESTRUCTIVE=true`.

## Installation

shortcut-mcp is **not published to PyPI** — install it from source:

```bash
uv tool install git+https://github.com/millsymills-com/shortcut-mcp
```

This puts a `shortcut-mcp` executable on your PATH. To run without installing
(handy for MCP clients), use `uvx --from git+… shortcut-mcp` instead — see
[Client configuration](#client-configuration).

## Usage

Set `SHORTCUT_API_TOKEN` and run:

```bash
shortcut-mcp
```

## Client configuration

shortcut-mcp speaks MCP over stdio, so any stdio-capable client launches it the
same way: a `command`, optional `args`, and an `env` block carrying your token.

Because there is no PyPI package, the `command` is either the installed
`shortcut-mcp` binary or `uvx` resolving the package straight from git. Pick one:

- **Installed** (`uv tool install git+…` first): `"command": "shortcut-mcp"`.
  If your client doesn't inherit your shell PATH, use the absolute path that
  `uv tool install` prints (or run `which shortcut-mcp` to find it).
- **No install** (`uvx` builds it on first launch, then caches):
  `"command": "uvx", "args": ["--from", "git+https://github.com/millsymills-com/shortcut-mcp", "shortcut-mcp"]`.

### Claude Desktop

Edit `claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/`,
Windows: `%APPDATA%\Claude\`):

```json
{
  "mcpServers": {
    "shortcut": {
      "command": "shortcut-mcp",
      "env": { "SHORTCUT_API_TOKEN": "your-token" }
    }
  }
}
```

### Cursor

Edit `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (per-project):

```json
{
  "mcpServers": {
    "shortcut": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/millsymills-com/shortcut-mcp", "shortcut-mcp"],
      "env": { "SHORTCUT_API_TOKEN": "your-token" }
    }
  }
}
```

### Windsurf

Edit `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "shortcut": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/millsymills-com/shortcut-mcp", "shortcut-mcp"],
      "env": { "SHORTCUT_API_TOKEN": "your-token" }
    }
  }
}
```

### Generic stdio client

Any other MCP client that launches a subprocess uses the same three pieces:

```json
{
  "command": "shortcut-mcp",
  "args": [],
  "env": { "SHORTCUT_API_TOKEN": "your-token" }
}
```

Add `"SHORTCUT_MODE": "readwrite"` (and `"SHORTCUT_ALLOW_DESTRUCTIVE": "true"`)
to the `env` block to expose the write and destructive tiers — see
[Safety model](#safety-model).

## Configuration

| Variable | Default | Description |
|---|---|---|
| `SHORTCUT_API_TOKEN` | _(required)_ | Shortcut API token |
| `SHORTCUT_MODE` | `readonly` | `readonly` or `readwrite` |
| `SHORTCUT_ALLOW_DESTRUCTIVE` | `false` | With `readwrite`, expose the 21 destructive tools (deletes + workspace toggles) |
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
| `all` | all 26 modules (65 read + 51 write + 21 destructive tools at the matching gates) |

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
| `readonly` (default) | _(ignored)_ | 65 read tools only |
| `readwrite` | `false` | 65 read + 51 write tools (116 total) |
| `readwrite` | `true` | 65 read + 51 write + 21 destructive tools (137 total) |

Write tools are hidden entirely in readonly mode — they do not appear in
`list_tools()` output and cannot be called. Setting `SHORTCUT_MODE=readwrite`
is required to expose them. Destructive tools require **both**
`SHORTCUT_MODE=readwrite` and `SHORTCUT_ALLOW_DESTRUCTIVE=true`; with either gate
unset they stay hidden. Each delete handler also calls a runtime guard that
raises `mode_denied` if reached without both gates.

## Tool catalog

`list_*` tools return a shaped envelope `{items: [...], truncated: bool, total?: int}`
and accept a `limit` parameter (default 50; search tools default 25). `get_*`
tools return the full API object.

The catalog below is generated from the live tool registry by
`scripts/generate_tool_catalog.py` and verified in CI — edit a tool's
`description` in the source and run the script to refresh it. Tier headers
track the gates in [Safety model](#safety-model).

**A couple of tools to know:**

- `shortcut_update_story` **replaces** the `labels` and `owner_ids` arrays — use
  `shortcut_add_story_labels` / `shortcut_add_story_owners` to append instead.
- There is **no `delete_group`** — the Shortcut API exposes no `DELETE /groups/{id}`.

<!-- BEGIN GENERATED TOOL CATALOG -->

### Read tools (65)

#### story (3 tools)

- `shortcut_get_story` — Fetch a Shortcut story by its numeric ID.
- `shortcut_list_story_history` — List the change history for a story (most recent first).
- `shortcut_list_story_sub_tasks` — List a story's sub-tasks — the child stories under it (summary rows). Distinct from checklist tasks (see shortcut_get_story_task).

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

- `shortcut_list_repositories` — List all VCS repositories linked to the workspace (summary rows).
- `shortcut_get_repository` — Fetch one VCS repository by ID (full object).

#### external_link (1 tool)

- `shortcut_list_external_link_stories` — List the stories that reference a given external link URL (summary rows).

#### key_result (1 tool)

- `shortcut_get_key_result` — Fetch one objective key-result by ID (full object).

#### custom_field (2 tools)

- `shortcut_list_custom_fields` — List all custom fields defined in the workspace (summary rows).
- `shortcut_get_custom_field` — Fetch one custom field by ID (full object, including enum values).

#### category (4 tools)

- `shortcut_list_categories` — List all categories (summary rows).
- `shortcut_get_category` — Fetch one category by ID (full object).
- `shortcut_list_category_milestones` — List the milestones associated with a category (summary rows).
- `shortcut_list_category_objectives` — List the objectives associated with a category (summary rows).

#### entity_template (2 tools)

- `shortcut_list_entity_templates` — List all story templates in the workspace (summary rows).
- `shortcut_get_entity_template` — Fetch one story template by ID (full object, including story_contents).

#### document (5 tools)

- `shortcut_list_documents` — List all documents in the workspace (summary rows).
- `shortcut_get_document` — Fetch one document by ID (full object, including markdown content).
- `shortcut_list_document_epics` — List the epics linked to a document (summary rows).
- `shortcut_load_document_tiptap` — Load a document's content as Tiptap JSON (rich-text editor format).
- `shortcut_search_documents` — Search documents by title (substring match). Returns shaped summary rows.

#### health (4 tools)

- `shortcut_get_epic_health` — Fetch an epic's current health (full object).
- `shortcut_list_epic_health_history` — List an epic's health history, most recent first (summary rows).
- `shortcut_get_objective_health` — Fetch an objective's current health (full object).
- `shortcut_list_objective_health_history` — List an objective's health history, most recent first (summary rows).

#### search (6 tools)

- `shortcut_search_stories` — Search stories with Shortcut query syntax (e.g. 'state:done owner:me').
- `shortcut_search_epics` — Search epics with Shortcut query syntax.
- `shortcut_search_iterations` — Search iterations with Shortcut query syntax.
- `shortcut_search_objectives` — Search objectives with Shortcut query syntax.
- `shortcut_search` — Global multi-entity search. Returns {stories: {items, truncated}, epics: {items, truncated}} — NOT a top-level items list. For a single entity use shortcut_search_stories / shortcut_search_epics.
- `shortcut_query_stories` — Search stories by a structured filter. Supported filters: archived, owner_ids, workflow_state_id, epic_id (POST query; read-only despite POST).

### Write tools (51)

#### story (9 tools)

- `shortcut_create_story` — Create a new Shortcut story. Returns the created story object.
- `shortcut_update_story` — Update fields on an existing Shortcut story. Replaces labels/owner_ids with the values given. To add without removing, use shortcut_add_story_labels / shortcut_add_story_owners.
- `shortcut_archive_story` — Archive a Shortcut story (sets archived=true).
- `shortcut_unarchive_story` — Unarchive a Shortcut story (sets archived=false).
- `shortcut_add_story_labels` — Add labels to a story without removing existing ones. Fetches the current label set, merges the new names (deduplicated, order preserved), then PUTs the merged list.
- `shortcut_add_story_owners` — Add owners to a story without removing existing ones. Fetches the current owner_ids, merges the new ids (deduplicated, order preserved), then PUTs the merged list.
- `shortcut_bulk_create_stories` — Create multiple Shortcut stories in a single request (POST /stories/bulk).
- `shortcut_bulk_update_stories` — Update multiple Shortcut stories in a single request (PUT /stories/bulk).
- `shortcut_create_story_from_template` — Create a new Shortcut story from a story template (POST /stories/from-template).

#### story_comment (4 tools)

- `shortcut_create_story_comment` — Create a comment on a story.
- `shortcut_update_story_comment` — Update the text of an existing story comment.
- `shortcut_add_story_comment_reaction` — Add an emoji reaction to a story comment.
- `shortcut_remove_story_comment_reaction` — Remove an emoji reaction from a story comment.

#### story_task (2 tools)

- `shortcut_create_story_task` — Create a task (checklist item) on a story.
- `shortcut_update_story_task` — Update a task on a story (description, completion status, or both).

#### story_link (2 tools)

- `shortcut_create_story_link` — Create a relationship between two stories. verb must be one of: blocks, duplicates, relates to.
- `shortcut_update_story_link` — Update the verb on an existing story link.

#### epic (4 tools)

- `shortcut_create_epic` — Create a new Shortcut epic. Returns the created epic object.
- `shortcut_update_epic` — Update fields on an existing Shortcut epic.
- `shortcut_archive_epic` — Archive a Shortcut epic (sets archived=true).
- `shortcut_unarchive_epic` — Unarchive a Shortcut epic (sets archived=false).

#### epic_comment (3 tools)

- `shortcut_create_epic_comment` — Create a comment on an epic.
- `shortcut_create_epic_comment_reply` — Create a reply to an existing epic comment (POST on the comment id creates a reply).
- `shortcut_update_epic_comment` — Update the text of an existing epic comment.

#### iteration (2 tools)

- `shortcut_create_iteration` — Create a new Shortcut iteration. Returns the created iteration object.
- `shortcut_update_iteration` — Update fields on an existing Shortcut iteration.

#### objective (2 tools)

- `shortcut_create_objective` — Create a new Shortcut objective. Returns the created objective object.
- `shortcut_update_objective` — Update fields on an existing Shortcut objective.

#### group (2 tools)

- `shortcut_create_group` — Create a new Shortcut group/team. Returns the created group object.
- `shortcut_update_group` — Update fields on an existing Shortcut group/team.

#### label (2 tools)

- `shortcut_create_label` — Create a new Shortcut label. Returns the created label object.
- `shortcut_update_label` — Update fields on an existing Shortcut label.

#### project (2 tools)

- `shortcut_create_project` — Create a new Shortcut project. Returns the created project object.
- `shortcut_update_project` — Update fields on an existing Shortcut project.

#### file (2 tools)

- `shortcut_upload_file` — Upload a local file to Shortcut. The server reads ANY filesystem path readable by its process and uploads the bytes — do not expose this server to untrusted prompts when sensitive files are on disk. Requires SHORTCUT_MODE=readwrite.
- `shortcut_update_file` — Update metadata on an existing uploaded file.

#### linked_file (2 tools)

- `shortcut_create_linked_file` — Create a new Shortcut linked file. Returns the created linked file object.
- `shortcut_update_linked_file` — Update fields on an existing Shortcut linked file.

#### key_result (1 tool)

- `shortcut_update_key_result` — Update an objective key-result. Value args take a KeyResultValue object: {"numeric_value": "<decimal string>"} or {"boolean_value": <bool>}.

#### custom_field (1 tool)

- `shortcut_update_custom_field` — Update a custom field's name, description, enabled state, or icon set.

#### category (2 tools)

- `shortcut_create_category` — Create a new category. Returns the created category object.
- `shortcut_update_category` — Update a category's name, color, or archived state.

#### entity_template (2 tools)

- `shortcut_create_entity_template` — Create a story template. story_contents is the template body (a CreateStoryContents object: story_type, name, description, tasks, labels, etc.).
- `shortcut_update_entity_template` — Update a story template's name or story_contents body.

#### document (4 tools)

- `shortcut_create_document` — Create a document. content_format defaults to the API default (markdown).
- `shortcut_update_document` — Update a document's title, content, or content_format.
- `shortcut_link_document_to_epic` — Link a document to an epic (reversible association).
- `shortcut_unlink_document_from_epic` — Remove the link between a document and an epic (reversible; neither is deleted).

#### health (3 tools)

- `shortcut_create_epic_health` — Set an epic's health status (At Risk / On Track / Off Track / No Health), with optional text.
- `shortcut_create_objective_health` — Set an objective's health (At Risk / On Track / Off Track / No Health), with optional text.
- `shortcut_update_health` — Update an existing health entry's status and/or text by its health ID.

### Destructive tools (21)

#### story (2 tools)

- `shortcut_delete_story` — Permanently delete a Shortcut story. Irreversible. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.
- `shortcut_bulk_delete_stories` — Permanently delete multiple stories in one request (DELETE /stories/bulk). Irreversible. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.

#### story_comment (1 tool)

- `shortcut_delete_story_comment` — Permanently delete a comment on a story. Irreversible. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.

#### story_task (1 tool)

- `shortcut_delete_story_task` — Permanently delete a task on a story. Irreversible. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.

#### story_link (1 tool)

- `shortcut_delete_story_link` — Permanently delete a story link. Irreversible. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.

#### epic (1 tool)

- `shortcut_delete_epic` — Permanently delete an epic. Irreversible. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.

#### epic_comment (1 tool)

- `shortcut_delete_epic_comment` — Permanently delete a comment on an epic. Irreversible. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.

#### iteration (1 tool)

- `shortcut_delete_iteration` — Permanently delete an iteration. Irreversible. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.

#### objective (1 tool)

- `shortcut_delete_objective` — Permanently delete an objective. Irreversible. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.

#### label (1 tool)

- `shortcut_delete_label` — Permanently delete a label. Irreversible. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.

#### project (1 tool)

- `shortcut_delete_project` — Permanently delete a project. Irreversible. The Shortcut API rejects this with a 422 if the project still has stories — move or delete them first. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.

#### file (1 tool)

- `shortcut_delete_file` — Permanently delete an uploaded file. Irreversible. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.

#### linked_file (1 tool)

- `shortcut_delete_linked_file` — Permanently delete a linked file. Irreversible. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.

#### custom_field (1 tool)

- `shortcut_delete_custom_field` — Permanently delete a custom field. Irreversible. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.

#### category (1 tool)

- `shortcut_delete_category` — Permanently delete a category. Irreversible. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.

#### entity_template (1 tool)

- `shortcut_delete_entity_template` — Permanently delete a story template. Irreversible. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.

#### document (1 tool)

- `shortcut_delete_document` — Permanently delete a document. Irreversible. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.

#### feature_toggle (4 tools)

- `shortcut_enable_iterations` — WORKSPACE-WIDE: enable the Iterations feature for the entire workspace. Affects every member. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.
- `shortcut_disable_iterations` — WORKSPACE-WIDE: disable the Iterations feature for the entire workspace. Affects every member. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.
- `shortcut_enable_story_templates` — WORKSPACE-WIDE: enable Story Templates for the entire workspace. Affects every member. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.
- `shortcut_disable_story_templates` — WORKSPACE-WIDE: disable Story Templates for the entire workspace. Affects every member. Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true.

<!-- END GENERATED TOOL CATALOG -->

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
