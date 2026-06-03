# Idempotent reconcile

Goal: a re-run produces zero duplicates and applies only the real diff.

## Stable identity (required)
On create, stamp every story with a deterministic
`external_id = "<repo>:<objective-slug>/<epic-slug>/<story-slug>"`
(each slug = kebab-case of that entity's title). This is the primary match key
and is NOT optional — without it, story matching falls back to fragile titles
and re-runs can duplicate stories.

Objectives and epics have no `external_id` via the MCP tools, so they match by
name. Their names are taken verbatim from version/workstream headings and are
stable, so name-matching is reliable for those two tiers.

## Matching order
1. Objectives: `shortcut_list_objectives` → match planned Objective by **name**.
2. Epics: within a matched Objective, `shortcut_list_objective_epics` → match by **name**.
3. Stories: within a matched Epic, `shortcut_list_epic_stories` →
   a. match by **`external_id`** when present (preferred);
   b. else fall back to **name**.

## Classification
For every planned item:
- **CREATE** — no match exists.
- **UPDATE** — matched, but state, description, or embedded links differ.
- **UNCHANGED** — matched and equal.

## Ambiguity guard (legacy imports)
If a matched epic contains existing stories whose `external_id` is null AND some
planned story titles don't match any existing title, you cannot tell a genuine
new story from a renamed one. Do NOT auto-create: surface these in the dry-run
as "ambiguous (possible rename)" and ask the user. Recommend a one-time
`external_id` backfill on the legacy stories to make future runs clean.

## Notes
- Two projects may share a story title; matching is always scoped to the parent
  epic, so they never collide.
- Items present in Shortcut but absent from the repo plan → report as
  archive-candidates (flag only; never archive).
