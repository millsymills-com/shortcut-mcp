# shortcut-import — Repeatable Project-to-Shortcut Import Skill

**Date:** 2026-06-01
**Status:** Approved design; implementation pending
**Purpose:** Make "lifting and dropping" an existing repo (any maturity level)
into Shortcut a repeatable, interactive, idempotent process — packaged as a
Claude Code skill that uses the `shortcut-mcp` server.

## Background

The first instance of this was done by hand for `flipperzero-mcp`: read the
repo's specs/CHANGELOG/issues, derived a version→Objective / workstream→Epic /
task→Story tree, inferred real done/in-progress state, bulk-created the tree,
cross-linked GitHub issues, then revalidated against Shortcut. This skill
generalizes that procedure so it runs the same way for every project and stays
correct on re-runs as projects mature.

## Decisions (locked during brainstorming)

| Decision | Choice |
|---|---|
| Mechanism | **Skill** (`~/.claude/skills/shortcut-import/`), optional `/shortcut-import` slash-command wrapper. Not a subagent (fights the approval-gate model) and not a plain runbook (a skill is a runbook Claude executes). |
| Run mode | **Interactive with judgment** — invoked per project in a Claude Code session; Claude reads the repo, proposes the tree, the user approves, then it writes and validates. |
| Re-run behavior | **Idempotent sync** — re-running detects what already exists in Shortcut, updates states/links, adds newly-appeared work, never duplicates. |
| State source | **Inferred** from repo signals, **shown in the dry-run for override**. |
| GitHub linking | **Auto cross-link** stories/epics to GH issues when the repo has them. |
| Removed work | **Flagged, never auto-archived.** |
| Destructive ops | Never used. `readonly` mode → abort with guidance. |

## Canonical mapping

Default heuristic, applied to every project:

| Shortcut entity | Source in repo | Notes |
|---|---|---|
| **Objective** (milestone) | a **version / release** (`v0.1.0`, `v2`, …) | Fallback when a project has no versions: use major **phases or milestones** from specs. |
| **Epic** | a **workstream** within a version | Linked to its Objective via `milestone_id`. |
| **Story** | a **task / spec bullet** within a workstream | `epic_id` + `group_id` (team) + `workflow_state_id`. |

**State inference:**

- Objective/Epic/Story → **done** when the work is shipped (in CHANGELOG under a
  tagged release, merged, or the tool/feature exists in code).
- → **in progress** when an open issue/branch shows partial work, or the version
  is the current unreleased line.
- → **to do** when it exists only as a spec/plan with no implementation.

**`story_type` heuristic:** new tool/capability → `feature`; tests/CI/docs/
hygiene/renames → `chore`; defect work → `bug`.

**Deterministic story titles:** so a re-run regenerates identical names (titles
feed the name fallback and the `external_id` slug), derive each title in order:
(1) strip a leading conventional-commit prefix `^\w+(\([^)]*\))?:\s*` for
issue/commit sources (`fix(clients): x` → `x`); (2) strip a *trailing*
audit-metadata paren `\s*\([A-Z]+-\d+(,\s*[A-Z]+-\d+)*\)\.?$` (`… (PY-013).` →
`…`), never touching identifier parens like `main()`; (3) keep the clause before
any ` — ` em-dash; (4) drop a trailing "links/Links" clause. Push the full
original text into the description. The slug is the kebab-case of the result.
Never editorialize beyond these steps.

**GitHub links:** when the repo has issues, embed markdown links
(`[#27](https://github.com/<owner>/<repo>/issues/27)`) in the relevant story/epic
descriptions. Resolve `<owner>/<repo>` from the **git remote** (authoritative),
not from possibly-stale CHANGELOG/footer slugs.

## Skill structure

```
~/.claude/skills/shortcut-import/
├── SKILL.md                    # trigger + the 6-phase procedure
├── references/
│   ├── mapping.md              # mapping table + state/story_type heuristics
│   └── sync-algorithm.md       # idempotent reconcile algorithm (below)
└── (optional) /shortcut-import slash command wrapper
```

`SKILL.md` trigger description must fire on phrasings like "import/lift this
project into Shortcut", "drop this repo into Shortcut", "represent this roadmap
in Shortcut".

## Pipeline (6 phases)

### Phase 1 — Preflight

1. Confirm the Shortcut MCP tools are available and `SHORTCUT_MODE=readwrite`
   (if `readonly`, abort with the env-var guidance).
2. `shortcut_get_current_member` — confirm auth + identity.
3. `shortcut_list_workflows` — cache workflow state IDs (backlog/unstarted/
   started/done) and note the default workflow.
4. Cache epic state IDs (to do / in progress / done) by reading one existing
   epic or the workflow surface.
5. `shortcut_list_groups` — pick the team: if exactly one, use it and report
   which; otherwise ask the user.

### Phase 2 — Gather signals

Read, in the target repo:

- `CHANGELOG.md` (shipped surface, version boundaries).
- `docs/superpowers/specs/*` and any `plans/` (roadmap, workstreams, tasks).
- `git tag` + `git log` (what's released vs in-flight) and the **remote URL**
  (for issue links).
- `README.md` (current tool/feature surface).
- Open + closed GitHub issues via `gh issue list --state all` (status signals +
  linkable references).

Produce an internal model: versions → workstreams → tasks, each tagged with an
inferred state and (where applicable) a GH issue number.

### Phase 3 — Derive tree

Apply the canonical mapping and state/`story_type` heuristics to turn the signal
model into a concrete Objective/Epic/Story tree with inferred states and
embedded GH links. Use the version fallback for projects with no versions.

### Phase 4 — Reconcile (idempotent)

See `references/sync-algorithm.md`. Summary:

1. **Objectives/Epics — match by name.** `shortcut_list_objectives` → match each
   planned Objective by name; within it, `shortcut_list_objective_epics` → match
   Epics by name. Their names come verbatim from version/workstream headings and
   are stable, so name-matching is reliable for these two tiers.
2. **Stories — match by `external_id` first, name as fallback.** On create, every
   story is stamped with a **required** deterministic
   `external_id = "<repo>:<objective-slug>/<epic-slug>/<story-slug>"` (each slug
   is the kebab-case of that entity's title). On reconcile, match an existing
   story by `external_id` when present; fall back to name only for legacy stories
   that predate the stamp. `external_id` is **not optional** — story titles alone
   are too unstable (they are editorial paraphrases of source bullets) to be a
   reliable key, and without the stamp a re-run can duplicate stories.
3. Classify every planned item as **CREATE** (no match), **UPDATE** (matched but
   state/description/links differ), or **UNCHANGED**.

Matching is scoped to the parent, so two projects can share a story title
without colliding.

**Ambiguity guard (legacy imports).** If a matched epic contains existing stories
with null `external_id` *and* some planned titles don't match any existing title,
a genuine new story is indistinguishable from a rename. Do not auto-create —
surface these as "ambiguous (possible rename)" in the dry-run and ask. Recommend
a one-time `external_id` backfill on the legacy stories to make future runs clean.

### Phase 5 — Dry-run approval gate

Present, and **write nothing** until the user approves:

- chosen team + workflow;
- counts: N objectives / M epics / K stories, broken into CREATE / UPDATE /
  UNCHANGED;
- the per-item diff for anything being created or changed (esp. state changes);
- any **ambiguous (possible rename)** stories (matched epic, legacy null
  `external_id`, title doesn't match) — asked about, never silently created;
- any **flagged** items: work that exists in Shortcut but no longer appears in
  the repo (candidate for archive — reported, never auto-archived).

### Phase 6 — Execute + validate

1. Create/update Objectives (`shortcut_create_objective` / `update_objective`),
   set states.
2. Create/update Epics (`shortcut_create_epic` with `milestone_id` /
   `update_epic` with `epic_state_id`).
3. Create Stories (`shortcut_bulk_create_stories` with `epic_id` + `group_id` +
   `workflow_state_id` + description + the required `external_id` stamp) /
   `update_story` for changed ones.
4. **Revalidate**: re-read objectives, `list_objective_epics`,
   `list_epic_stories`, and spot-fetch stories that carry GH links; cross-check
   counts, parent mapping, states, and that links persisted.
5. Report a summary table with `app.shortcut.com` URLs at all three levels.

## Edge cases

- **No team / multiple teams** — single team auto-used (reported); multiple →
  ask.
- **`readonly` mode** — abort before any read-tree work with a one-line fix
  (`SHORTCUT_MODE=readwrite`).
- **Project with no versions** — fall back to phases/milestones as Objectives.
- **Stale repo slugs** — derive issue-link owner/repo from `git remote`, and if a
  CHANGELOG/footer slug disagrees, flag it (don't silently trust it).
- **Partial prior run** — idempotent reconcile makes a re-run safe; it fills gaps
  rather than duplicating.
- **Removed work** — reported as archive candidates; never auto-archived (archive
  is a destructive-ish op and out of scope).

## Non-goals (YAGNI)

- No unattended/CI execution, no manifest format, no background agent.
- No automatic archiving or deletion of Shortcut entities.
- No iterations/sprint planning, owners, estimates, or labels in v1 (can be
  added later if a project needs them).
- No bidirectional sync (Shortcut → repo). One direction only: repo → Shortcut.

## Success criteria

- Running the skill on a fresh project produces the correct Objective/Epic/Story
  tree with accurate inferred states and GH links, after one approval.
- Re-running on an already-imported project makes **zero** duplicates and applies
  only the real diff (new work + state advances).
- The dry-run gate always precedes writes.
- Post-run validation confirms counts/mapping/links match the plan.
