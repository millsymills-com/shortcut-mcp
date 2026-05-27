# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **v0.5 niche read modules — 4 read tools + 1 write tool** across 3 new resource
  modules (exposed under `SHORTCUT_PROFILE=all` or an explicit `SHORTCUT_TOOLS`
  allowlist): `list_repositories` / `get_repository`, `list_external_link_stories`,
  `get_key_result`, and `update_key_result` (write-tier). Brings totals to 47 read +
  39 write + 13 destructive tools across 20 modules.

### Changed

- Transport errors `RemoteProtocolError` ("server disconnected"), `DecodingError`
  and `TooManyRedirects` are now classified as non-retryable protocol failures
  rather than connection errors, so a GET no longer retries them.

### Security

- Contract cassettes additionally redact member `gravatar_hash` (an MD5 of the
  real email) and `mention_name`; the privacy guard test fails on any future
  recording that leaks them.

## [0.4.0] - 2026-05-26

### Added

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

## [0.3.0] - 2026-05-26

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

[Unreleased]: https://github.com/millsymills-com/shortcut-mcp/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/millsymills-com/shortcut-mcp/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/millsymills-com/shortcut-mcp/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/millsymills-com/shortcut-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/millsymills-com/shortcut-mcp/releases/tag/v0.1.0
