# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **v0.3 write tier — 38 write tools across all resource modules**, gated by
  `SHORTCUT_MODE=readwrite` (hidden entirely in readonly mode):
  - `story`: create, update, archive, unarchive, add labels, add owners,
    bulk create, bulk update, create from template (9 tools)
  - `story_comment`: create, update, add/remove emoji reaction (4 tools)
  - `story_task`: create, update (2 tools)
  - `story_link`: create, update (2 tools)
  - `epic`: create, update, archive, unarchive (4 tools)
  - `epic_comment`: create, reply, update (3 tools)
  - `iteration`: create, update (2 tools)
  - `objective`: create, update (2 tools)
  - `group`: create, update (2 tools)
  - `label`: create, update (2 tools)
  - `project`: create, update (2 tools)
  - `file`: upload (multipart), update metadata (2 tools)
  - `linked_file`: create, update (2 tools)
- **`require_writes` runtime guard** — write tools raise `ToolError` (`mode_denied`)
  if called outside a `readwrite` context, even if somehow invoked directly.
- **Multipart upload + DELETE-with-body client support** in `ShortcutClient`.

## [0.2.0] - 2026-05-23

### Added

- **Complete read surface — 43 read tools across 17 resource modules:**
  - `story`: get story, list story history
  - `story_comment`: list and get story comments
  - `story_task`: get story task
  - `story_link`: get story link
  - `epic`: list epics, get epic, list epic stories
  - `epic_comment`: list and get epic comments
  - `epic_workflow`: get epic workflow
  - `iteration`: list iterations, get iteration, list iteration stories
  - `objective`: list objectives, get objective, list objective epics
  - `member`: list members, get member, get current member
  - `group`: list groups, get group, list group stories
  - `workflow`: list workflows, get workflow
  - `label`: list labels, get label, list label stories, list label epics
  - `project`: list projects, get project, list project stories
  - `file`: list files, get file
  - `linked_file`: list linked files, get linked file
  - `search`: search stories/epics/iterations/objectives, global search, query stories by filter

- **Tool gating via `SHORTCUT_PROFILE` and `SHORTCUT_TOOLS`:**
  - `SHORTCUT_PROFILE` selects a named module bundle: `core` (default), `planning`, `files`, or `all`.
  - `SHORTCUT_TOOLS` accepts a comma-separated module allowlist that overrides the profile. Unknown module names are rejected at startup.

- **Response shaping:** `list_*` tools return `{items: [...], truncated: bool, total?: int}` envelopes with a `limit` parameter (default 50; search tools default 25). Search tools follow the `{data, next, total}` cursor API.

## [0.1.0] - 2026-05-01

### Added

- Initial server scaffold with FastMCP.
- `shortcut_get_story` tracer-bullet tool.
- `SHORTCUT_MODE` and `SHORTCUT_ALLOW_DESTRUCTIVE` safety gates.
- `SHORTCUT_API_TOKEN` authentication via env / `.env` file.
