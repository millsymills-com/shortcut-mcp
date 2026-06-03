---
name: shortcut-import
description: Lift an existing repo into Shortcut as Objectives/Epics/Stories via the shortcut-mcp server. Idempotent and interactive — reads the repo, proposes a tree with inferred states, shows a dry-run diff, writes only after approval, then validates. Use when the user wants to import, lift, drop, or represent a project/roadmap in Shortcut.
---

# Shortcut Import

Interactively and idempotently mirror a repo's roadmap into Shortcut. Read-tree →
derive → reconcile → dry-run approval → write → validate. Never duplicates on
re-run; never auto-archives; never uses destructive Shortcut ops.

## When to use

User asks to import / lift / drop / represent a repo or its roadmap in Shortcut.

## Procedure

Create a TodoWrite item per phase, then work them in order.

### Phase 1 — Preflight
- Confirm `mcp__shortcut__*` tools are available and the server runs in
  `SHORTCUT_MODE=readwrite`. This is the **shortcut-mcp server's** env (its `.env`
  or MCP config `env`), not the calling shell — the shell will show it unset even
  when writes are enabled. If it is readonly, STOP and tell the user to set
  `SHORTCUT_MODE=readwrite` and reload.
- `shortcut_get_current_member` (auth + identity).
- `shortcut_list_workflows` → cache state IDs (backlog/unstarted/started/done) +
  default workflow.
- Cache epic state IDs (to do / in progress / done) from an existing epic.
- `shortcut_list_groups` → pick the team: one → use it and report; many → ask.

### Phase 2 — Gather signals
Read in the target repo: `CHANGELOG.md`; `docs/superpowers/specs/*` and any
`plans/`; `git tag` + `git log` + the **remote URL**; `README.md`; the tool
surface; and `gh issue list --state all`. Build a versions→workstreams→tasks
model, each tagged with an inferred state and any GH issue number.

### Phase 3 — Derive tree
Apply `references/mapping.md` (mapping + state + story_type + GH-link rules) to
turn the signal model into a concrete Objective/Epic/Story tree.

### Phase 4 — Reconcile (idempotent)
Follow `references/sync-algorithm.md`. Produce a CREATE / UPDATE / UNCHANGED
classification for every planned item by matching against existing Shortcut
objectives/epics/stories.

### Phase 5 — Dry-run approval gate
Present team + workflow, counts (CREATE/UPDATE/UNCHANGED), the per-item diff for
created/changed items, any flagged archive-candidates, and any
**ambiguous (possible rename)** stories per `references/sync-algorithm.md`.
WRITE NOTHING until the user approves; ask before creating ambiguous stories.
When a workstream is a cluster of N similar issues (e.g. a bug-fix round), offer
the user a granularity choice at this gate — one story per issue vs a single
rolled-up story — rather than deciding for them.

### Phase 6 — Execute + validate
Write in tiers:
1. **Objectives** — `create_objective` accepts `state` (`to do`/`in progress`/
   `done`) directly on create.
2. **Epics** — `create_epic` takes `milestone_id` but has **no** state field;
   after creating, set state with `update_epic(epic_id, epic_state_id=<int>)`.
3. **Stories** — `bulk_create_stories` with `epic_id`+`group_id`+
   `workflow_state_id`+`description`, stamping each with its deterministic
   `external_id` (see `references/sync-algorithm.md`); `update_story` for changes.

Then re-read (`list_objectives`, `list_objective_epics`, `list_epic_stories`,
spot-fetch link-bearing stories) and cross-check counts, parent mapping, states,
and persisted links. Report a summary table with `app.shortcut.com` URLs.

**Tool-arg gotchas (shortcut-mcp):** the read/verify tools take integer IDs named
`objective_id` / `epic_id` / `story_id` (not `*_public_id`); `epic_state_id` and
`workflow_state_id` are integers sourced from Phase 1's cache, not strings.

## Rules
- Idempotent: re-runs never duplicate.
- Never auto-archive removed work — flag it.
- Never use destructive Shortcut tools.
- Derive issue-link `owner/repo` from `git remote`, not CHANGELOG footers. If the
  repo's own docs (README/CHANGELOG/pyproject/User-Agent) use a different,
  redirecting slug, flag it as a repo-side fix too — the source should match the
  links you persist in Shortcut, not just be silently overridden.
