# shortcut-mcp

Python FastMCP server for the Shortcut REST API. v0.2 ships a complete read
surface: **43 read tools across 17 resource modules**. Write and destructive
tools are planned for v0.3/v0.4 and not yet present.

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
| `SHORTCUT_ALLOW_DESTRUCTIVE` | `false` | Enable destructive tools (v0.4+, not yet shipped) |
| `SHORTCUT_PROFILE` | `core` | Named tool bundle — see [Tool profiles](#tool-profiles--gating) |
| `SHORTCUT_TOOLS` | _(unset)_ | Comma-separated module allowlist; overrides `SHORTCUT_PROFILE` |
| `SHORTCUT_API_BASE_URL` | `https://api.app.shortcut.com/api/v3` | API base URL |
| `SHORTCUT_REQUEST_TIMEOUT` | `30` | Per-request timeout in seconds |
| `SHORTCUT_MAX_RETRIES` | `3` | Maximum retry attempts |

## Tool profiles & gating

`SHORTCUT_PROFILE` selects a named bundle of modules loaded at startup:

| Profile | Modules included |
|---|---|
| `core` (default) | story, story_comment, story_task, story_link, epic, epic_comment, epic_workflow, iteration, objective, member, workflow, label, search |
| `planning` | core + group, project |
| `files` | core + file, linked_file |
| `all` | all 17 modules (all 43 read tools) |

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
| `readwrite` | `false` | Read tools + write tools (v0.3+, not yet shipped) |
| `readwrite` | `true` | Read + write + destructive tools (v0.4+, not yet shipped) |

v0.2 is read-only. Setting `SHORTCUT_MODE=readwrite` has no effect until v0.3
ships write tools.

## Tool catalog

All 43 tools are read-only. `list_*` tools return a shaped envelope
`{items: [...], truncated: bool, total?: int}` and accept a `limit` parameter
(default 50; search tools default 25). `get_*` tools return the full API object.

### story (2 tools)

- `shortcut_get_story` — Fetch a story by numeric ID.
- `shortcut_list_story_history` — List change history for a story (most recent first).

### story_comment (2 tools)

- `shortcut_list_story_comments` — List comments on a story (summary rows).
- `shortcut_get_story_comment` — Fetch one story comment (full object).

### story_task (1 tool)

- `shortcut_get_story_task` — Fetch one task on a story (full object).

### story_link (1 tool)

- `shortcut_get_story_link` — Fetch one story link by ID (full object).

### epic (3 tools)

- `shortcut_list_epics` — List all epics (summary rows).
- `shortcut_get_epic` — Fetch one epic by ID (full object).
- `shortcut_list_epic_stories` — List the stories in an epic (summary rows).

### epic_comment (2 tools)

- `shortcut_list_epic_comments` — List comments on an epic (summary rows).
- `shortcut_get_epic_comment` — Fetch one epic comment (full object).

### epic_workflow (1 tool)

- `shortcut_get_epic_workflow` — Get the epic workflow (epic states).

### iteration (3 tools)

- `shortcut_list_iterations` — List all iterations (summary rows).
- `shortcut_get_iteration` — Fetch one iteration by ID (full object).
- `shortcut_list_iteration_stories` — List the stories in an iteration (summary rows).

### objective (3 tools)

- `shortcut_list_objectives` — List all objectives (summary rows).
- `shortcut_get_objective` — Fetch one objective by ID (full object).
- `shortcut_list_objective_epics` — List the epics under an objective (summary rows).

### member (3 tools)

- `shortcut_list_members` — List all members (summary rows).
- `shortcut_get_member` — Fetch one member by UUID (full object).
- `shortcut_get_current_member` — Fetch the authenticated member (full object).

### group (3 tools)

- `shortcut_list_groups` — List all groups/teams (summary rows).
- `shortcut_get_group` — Fetch one group by UUID (full object).
- `shortcut_list_group_stories` — List the stories owned by a group (summary rows).

### workflow (2 tools)

- `shortcut_list_workflows` — List all workflows (summary rows).
- `shortcut_get_workflow` — Fetch one workflow by ID (full object).

### label (4 tools)

- `shortcut_list_labels` — List all labels (summary rows).
- `shortcut_get_label` — Fetch one label by ID (full object).
- `shortcut_list_label_stories` — List the stories with a label (summary rows).
- `shortcut_list_label_epics` — List the epics with a label (summary rows).

### project (3 tools)

- `shortcut_list_projects` — List all projects (summary rows).
- `shortcut_get_project` — Fetch one project by ID (full object).
- `shortcut_list_project_stories` — List the stories in a project (summary rows).

### file (2 tools)

- `shortcut_list_files` — List all uploaded files (summary rows).
- `shortcut_get_file` — Fetch one uploaded file by ID (full object).

### linked_file (2 tools)

- `shortcut_list_linked_files` — List all linked files (summary rows).
- `shortcut_get_linked_file` — Fetch one linked file by ID (full object).

### search (6 tools)

- `shortcut_search_stories` — Search stories with Shortcut query syntax (e.g. `state:done owner:me`).
- `shortcut_search_epics` — Search epics with Shortcut query syntax.
- `shortcut_search_iterations` — Search iterations with Shortcut query syntax.
- `shortcut_search_objectives` — Search objectives with Shortcut query syntax.
- `shortcut_search` — Global multi-entity search; returns `{stories: {items, truncated}, epics: {items, truncated}}`.
- `shortcut_query_stories` — Search stories by structured filter (POST query; read-only despite POST).
