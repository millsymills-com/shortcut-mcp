# shortcut-import Skill — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code skill, `shortcut-import`, that interactively and
idempotently lifts any repo into Shortcut (Objective/Epic/Story) via the
`shortcut-mcp` server.

**Architecture:** The skill is Markdown instructions (no runtime code). `SKILL.md`
holds the 6-phase procedure; two `references/` files hold the mapping heuristics
and the idempotent-reconcile algorithm (progressive disclosure — loaded only when
that phase runs). The skill drives the existing `mcp__shortcut__*` tools and `gh`.
Verification is by exercising the skill against real workspace repos, including a
re-run against the already-imported `flipperzero-mcp` to prove idempotency.

**Tech Stack:** Markdown skill (frontmatter `name`+`description`), `shortcut-mcp`
MCP tools, `gh` CLI, `git`. Source of truth for content:
`shortcut-mcp/docs/superpowers/specs/2026-06-01-shortcut-import-skill-design.md`.

---

## File Structure

Skills install as symlinks on this machine (verified): real files live under
`~/.agents/skills/<name>/`, surfaced via `~/.claude/skills/<name>`. Frontmatter is
`name` + `description` only.

- Create: `~/.agents/skills/shortcut-import/SKILL.md` — trigger + 6-phase procedure.
- Create: `~/.agents/skills/shortcut-import/references/mapping.md` — mapping table,
  state inference, `story_type` heuristic, GH-link rules.
- Create: `~/.agents/skills/shortcut-import/references/sync-algorithm.md` —
  idempotent reconcile (match → classify CREATE/UPDATE/UNCHANGED).
- Create (symlink): `~/.claude/skills/shortcut-import` →
  `../../.agents/skills/shortcut-import`.
- Optional later: a tracked source copy (Task 8).

Neither skills tree is a git repo, so the skill files are not committed anywhere
by default. The spec and this plan remain committed in `shortcut-mcp`.

> **Post-build note.** The skill shipped and has since been refined from real
> imports (flipperzero-mcp, gandi-mcp). The transcribed snippets below are the
> original build seed; the **live skill** (`~/.agents/skills/shortcut-import/`)
> and the design **spec** are authoritative. Beyond the snippets here, the live
> files also carry the legacy-import ambiguity guard and full
> deterministic-title rules in `sync-algorithm.md` / `mapping.md`.

---

### Task 1: Scaffold skill + frontmatter + symlink, verify activation

**Files:**
- Create: `~/.agents/skills/shortcut-import/SKILL.md`
- Create (symlink): `~/.claude/skills/shortcut-import`

- [ ] **Step 1: Create the skill directory and reference subdir**

Run:
```bash
mkdir -p ~/.agents/skills/shortcut-import/references
```

- [ ] **Step 2: Write `SKILL.md` with frontmatter + title only (body comes next task)**

Write `~/.agents/skills/shortcut-import/SKILL.md`:
```markdown
---
name: shortcut-import
description: Lift an existing repo into Shortcut as Objectives/Epics/Stories via the shortcut-mcp server. Idempotent and interactive — reads the repo, proposes a tree with inferred states, shows a dry-run diff, writes only after approval, then validates. Use when the user wants to import, lift, drop, or represent a project/roadmap in Shortcut.
---

# Shortcut Import

Interactively and idempotently mirror a repo's roadmap into Shortcut. Read-tree →
derive → reconcile → dry-run approval → write → validate. Never duplicates on
re-run; never auto-archives; never uses destructive Shortcut ops.

<!-- procedure body added in Task 2 -->
```

- [ ] **Step 3: Create the symlink into the active skills dir**

Run:
```bash
ln -s ../../.agents/skills/shortcut-import ~/.claude/skills/shortcut-import
ls -l ~/.claude/skills/shortcut-import
```
Expected: symlink resolves to `../../.agents/skills/shortcut-import`.

- [ ] **Step 4: Verify the skill is discoverable**

Run:
```bash
test -f ~/.claude/skills/shortcut-import/SKILL.md && echo "resolves OK"
```
Expected: `resolves OK`. (The skill will appear in the skills list on the next
session; in-session activation is confirmed during the Task 6 dry-run.)

- [ ] **Step 5: No commit** — skills tree is not git-tracked. Proceed.

---

### Task 2: Author the 6-phase procedure in SKILL.md

**Files:**
- Modify: `~/.agents/skills/shortcut-import/SKILL.md`

The detailed procedure is fully specified in the design spec under
`## Pipeline (6 phases)` and `## Edge cases`. Transcribe it into `SKILL.md`,
replacing the `<!-- procedure body added in Task 2 -->` marker, using these exact
section headers and load-on-demand pointers to the reference files.

- [ ] **Step 1: Replace the marker with the procedure skeleton**

Append (replacing the marker comment) to `SKILL.md`:
```markdown
## When to use

User asks to import / lift / drop / represent a repo or its roadmap in Shortcut.

## Procedure

Create a TodoWrite item per phase, then work them in order.

### Phase 1 — Preflight
- Confirm `mcp__shortcut__*` tools are available and the server runs in
  `SHORTCUT_MODE=readwrite` — this is the shortcut-mcp server's env (its `.env` /
  MCP config `env`), not the calling shell, which shows it unset even when writes
  work. If readonly, STOP and tell the user to set `SHORTCUT_MODE=readwrite` and reload.
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
created/changed items, and any flagged archive-candidates. WRITE NOTHING until
the user approves. When a workstream is a cluster of N similar issues (e.g. a
bug-fix round), offer a granularity choice — one story per issue vs a single
rolled-up story — rather than deciding for them.

### Phase 6 — Execute + validate
Write in tiers: Objectives (`create_objective` takes `state` on create) → Epics
(`create_epic` takes `milestone_id` but **no** state; set state afterward with
`update_epic(epic_id, epic_state_id=<int>)`) → Stories (`bulk_create_stories`
with `epic_id`+`group_id`+`workflow_state_id`+description; `update_story` for
changes). Then re-read (`list_objectives`, `list_objective_epics`,
`list_epic_stories`, spot-fetch link-bearing stories) and cross-check counts,
parent mapping, states, and persisted links. Report a summary table with
`app.shortcut.com` URLs. Tool-arg gotcha: read tools take integer `objective_id`/
`epic_id`/`story_id` (not `*_public_id`); `epic_state_id`/`workflow_state_id` are
integers.

## Rules
- Idempotent: re-runs never duplicate.
- Never auto-archive removed work — flag it.
- Never use destructive Shortcut tools.
- Derive issue-link `owner/repo` from `git remote`, not CHANGELOG footers; if the
  repo's own docs use a different, redirecting slug, flag it as a repo-side fix.
```

- [ ] **Step 2: Verify the file is well-formed and references resolve**

Run:
```bash
grep -c '^### Phase' ~/.agents/skills/shortcut-import/SKILL.md
```
Expected: `6`.

- [ ] **Step 3: No commit** (untracked tree). Proceed.

---

### Task 3: Author references/mapping.md

**Files:**
- Create: `~/.agents/skills/shortcut-import/references/mapping.md`

- [ ] **Step 1: Write the mapping reference**

Write `~/.agents/skills/shortcut-import/references/mapping.md` transcribing the
spec's `## Canonical mapping` section verbatim:
```markdown
# Mapping rules

| Shortcut entity | Source in repo | Notes |
|---|---|---|
| Objective (milestone) | a version / release (v0.1.0, v2, …) | Fallback when no versions: major phases/milestones from specs. |
| Epic | a workstream within a version | Link to Objective via `milestone_id`. |
| Story | a task / spec bullet within a workstream | `epic_id` + `group_id` + `workflow_state_id`. |

## State inference
- done — shipped (CHANGELOG under a tagged release, merged, or the tool/feature
  exists in code).
- in progress — open issue/branch shows partial work, or it's the current
  unreleased version line.
- to do — exists only as a spec/plan, no implementation.

## story_type
new tool/capability → feature; tests/CI/docs/hygiene/renames → chore; defects → bug.

## Story titles (deterministic)
Regenerate identical names on re-run (the cleaned title is the `external_id` slug
and the name-match key). In order: (1) strip a leading conventional-commit prefix
`^\w+(\([^)]*\))?:\s*` and/or leading bracketed severity/category tags
`^(\[[A-Z][A-Z ]*\]\s*)+` (`[DOCS] x` → `x`) — required for idempotency; (2) strip
a trailing audit paren `\s*\([A-Z]+-\d+(,\s*[A-Z]+-\d+)*\)\.?$`; (3) keep the
clause before any ` — ` em-dash; (4) drop a trailing links clause. Put the full
original text in the description; the slug is the kebab-case of the result.

## GitHub links
When the repo has issues, embed markdown links
`[#N](https://github.com/<owner>/<repo>/issues/N)` in the relevant story/epic
descriptions. Resolve `<owner>/<repo>` from `git remote get-url origin`
(authoritative); if a CHANGELOG/footer slug disagrees, flag it.
```

- [ ] **Step 2: Verify**

Run:
```bash
grep -q 'milestone_id' ~/.agents/skills/shortcut-import/references/mapping.md && echo OK
```
Expected: `OK`.

---

### Task 4: Author references/sync-algorithm.md

**Files:**
- Create: `~/.agents/skills/shortcut-import/references/sync-algorithm.md`

- [ ] **Step 1: Write the reconcile algorithm**

Write `~/.agents/skills/shortcut-import/references/sync-algorithm.md`:
```markdown
# Idempotent reconcile

Goal: a re-run produces zero duplicates and applies only the real diff.

## Matching (name-scoped to parent)
1. `shortcut_list_objectives` → match each planned Objective by **name**.
2. For a matched Objective: `shortcut_list_objective_epics` → match Epics by name.
3. For a matched Epic: `shortcut_list_epic_stories` → match Stories by name.

Name match is the primary key. Optionally stamp each created story with
`external_id = "<repo>:<objective-slug>/<epic-slug>/<story-slug>"` (passed in the
`bulk_create_stories` story object) so future runs survive renames; read it back
when present and prefer it over the name match.

## Classification
For every planned item:
- **CREATE** — no match exists.
- **UPDATE** — matched, but state, description, or embedded links differ.
- **UNCHANGED** — matched and equal.

## Notes
- Objectives and epics have no `external_id` via the MCP tools — match by name.
- Two projects may share a story title; matching is always scoped to the parent
  epic, so they never collide.
- Items present in Shortcut but absent from the repo plan → report as
  archive-candidates (flag only; never archive).
```

- [ ] **Step 2: Verify**

Run:
```bash
grep -Eq 'CREATE|UPDATE|UNCHANGED' ~/.agents/skills/shortcut-import/references/sync-algorithm.md && echo OK
```
Expected: `OK`.

---

### Task 5: (Optional) slash-command wrapper

Skip unless you want `/shortcut-import` discoverability. The skill already
activates from natural-language triggers.

**Files:**
- Create: `~/.claude/commands/shortcut-import.md`

- [ ] **Step 1: Write the one-line wrapper**

Write `~/.claude/commands/shortcut-import.md`:
```markdown
---
description: Import a repo into Shortcut as Objectives/Epics/Stories (idempotent).
---
Invoke the `shortcut-import` skill for the current repo (or the repo at $ARGUMENTS).
```

- [ ] **Step 2: Verify it lists**

Run:
```bash
test -f ~/.claude/commands/shortcut-import.md && echo OK
```
Expected: `OK`.

---

### Task 6: Verify idempotency against flipperzero-mcp (acceptance test)

This is the strongest test: `flipperzero-mcp` is already fully imported
(Objectives 116–119, Epics 120–130, Stories 131–174). A dry-run must classify
everything as UNCHANGED and propose **zero** creates.

**Files:** none (exercises the skill).

- [ ] **Step 1: Define expected outcome**

Re-running the skill on `flipperzero-mcp` and stopping at the Phase 5 dry-run must
report: 4 objectives / 11 epics / 44 stories, all **UNCHANGED**; **0 CREATE**;
**0 duplicates**; no archive-candidate flags.

- [ ] **Step 2: Run the skill in dry-run**

In a Claude Code session at `~/Desktop/Projects/mcp-server-dev/flipperzero-mcp`,
trigger: "import this project into Shortcut." Let it run Phases 1–4 and STOP at
the Phase 5 dry-run. Do **not** approve writes.

- [ ] **Step 3: Verify the diff**

Confirm the dry-run shows 0 CREATE / 0 UPDATE-that-would-duplicate, all 59 items
matched as UNCHANGED. If any item shows CREATE, the name-matching in
`sync-algorithm.md` is wrong — fix matching (Task 4) and re-run this task.

Expected: PASS = all UNCHANGED, zero creates.

---

### Task 7: Verify fresh import against a not-yet-imported repo

**Files:** none (exercises the skill).

- [ ] **Step 1: Pick an un-imported, mature repo**

Use `gandi-mcp` (has CHANGELOG + multiple specs + likely GH issues). Confirm it
has no existing Shortcut objectives by name first (the skill does this in Phase 4).

- [ ] **Step 2: Run the skill in dry-run**

In a session at `~/Desktop/Projects/mcp-server-dev/gandi-mcp`, trigger the import
and STOP at the Phase 5 dry-run.

- [ ] **Step 3: Verify the proposed tree**

Confirm: Objectives correspond to versions/phases; Epics to workstreams; Stories
to tasks; states are inferred (shipped→done, spec-only→to do); GH links use the
slug from `git remote`. Sanity-check 3–4 items against the repo. Do not write
unless you actually want gandi-mcp in Shortcut.

Expected: PASS = a sensible, accurate tree with correct inferred states; all
classified CREATE (nothing pre-exists).

---

### Task 8: (Optional) Version-control the skill source

The skill lives in an untracked tree. If you want it tracked/shareable:

- [ ] **Step 1: Copy the source into a tracked location**

Run:
```bash
cp -R ~/.agents/skills/shortcut-import ~/Desktop/Projects/claude-defaults/skills/shortcut-import
```

- [ ] **Step 2: Commit in claude-defaults**

Run:
```bash
cd ~/Desktop/Projects/claude-defaults
git add skills/shortcut-import
git commit -m "feat: add shortcut-import skill"
```

(Leave the active install as the `~/.agents/skills` symlink target, or repoint the
symlink at the tracked copy — your call.)

---

## Self-Review

**Spec coverage:**
- Mechanism = skill + optional command → Tasks 1, 5. ✓
- 6-phase pipeline → Task 2. ✓
- Mapping + state + story_type + GH links → Task 3. ✓
- Idempotent reconcile → Task 4. ✓
- Dry-run approval gate → in SKILL.md Phase 5 (Task 2), exercised in Tasks 6–7. ✓
- Validation pass → SKILL.md Phase 6 (Task 2), exercised in Tasks 6–7. ✓
- Edge cases (readonly, no/many teams, no versions, stale slugs, partial prior
  run, removed work) → SKILL.md Rules + mapping/sync references (Tasks 2–4). ✓
- Idempotency success criterion → Task 6 (zero creates on re-run). ✓

**Placeholder scan:** No TBD/TODO; every file step contains the literal content to
write; verification steps give exact commands + expected output. ✓

**Consistency:** Phase names, tool names (`shortcut_*`), and the
CREATE/UPDATE/UNCHANGED vocabulary match across SKILL.md and both references. ✓
