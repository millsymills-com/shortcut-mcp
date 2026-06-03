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
Derive each title deterministically so a re-run regenerates identical names
(titles are the name fallback key and the `external_id` slug). Apply in order:

1. **Leading metadata prefix** (GitHub-issue/commit sources): strip a leading
   conventional-commit prefix — regex `^\w+(\([^)]*\))?:\s*` (e.g.
   `fix(clients): _seg crashes` → `_seg crashes`) — and/or one or more leading
   bracketed severity/category tags common in issue titles — regex
   `^(\[[A-Z][A-Z ]*\]\s*)+` (e.g. `[DOCS] CLAUDE.md errors` → `CLAUDE.md errors`,
   `[CRITICAL] _seg crash` → `_seg crash`). Stripping these is **required**, not
   cosmetic: the cleaned title is the `external_id` slug and the name-match key,
   so a run that keeps the tag and a run that strips it would not match and would
   duplicate every tagged story.
2. **Trailing audit/metadata paren**: strip a trailing parenthetical of audit
   codes and any trailing period — regex `\s*\([A-Z]+-\d+(,\s*[A-Z]+-\d+)*\)\.?$`
   (e.g. `… skeleton (PY-013, MCP-012).` → `… skeleton`). Do NOT touch parens
   that are part of an identifier such as `main()` or `configure_logging(...)`.
3. **Em-dash split**: if a leading clause is separated by ` — ` from a longer
   explanation, keep the part before the em-dash.
4. **"links"/"Links" marker**: drop a trailing `— links …` / `Links: …` clause.
5. Trim whitespace. The remainder is the title; put the FULL original text
   (paths, tool lists, identifiers, issue links) in the description.

The story slug (for `external_id`) is the kebab-case of the final title. Never
editorialize titles beyond these steps.

## GitHub links
When the repo has issues, embed markdown links
`[#N](https://github.com/<owner>/<repo>/issues/N)` in the relevant story/epic
descriptions. Resolve `<owner>/<repo>` from `git remote get-url origin`
(authoritative); if a CHANGELOG/footer slug disagrees, flag it.
