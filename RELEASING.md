# Releasing

shortcut-mcp ships as tagged GitHub Releases. There is no PyPI package — users
install from git (`uv tool install git+https://github.com/millsymills-com/shortcut-mcp`),
optionally pinning a tag (`...@vX.Y.Z`).

## Versioning

The version is single-sourced from the `version` field in `pyproject.toml`.
`shortcut_mcp.__version__` reads it at runtime via `importlib.metadata`, so the
only place a version literal appears is `pyproject.toml`. Do not hard-code a
version anywhere else.

Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html):

- **MAJOR** — incompatible tool/API changes (removed or renamed tools, changed
  response envelopes, stricter gating that hides previously-available tools).
- **MINOR** — backward-compatible additions (new tools, new optional config).
- **PATCH** — backward-compatible fixes (bug fixes, doc/test-only changes).

## Checklist

1. **Pre-flight.** `main` is green and your working tree is clean. Decide the
   semver bump from the `[Unreleased]` section of `CHANGELOG.md` (Added/Changed
   → MINOR, Fixed/Security with no behavior change → PATCH, removals → MAJOR).

2. **Bump the version** in `pyproject.toml`:

   ```toml
   [project]
   version = "X.Y.Z"
   ```

3. **Update `CHANGELOG.md`** (Keep a Changelog format):
   - Rename the `## [Unreleased]` heading to `## [X.Y.Z] - YYYY-MM-DD`.
   - Add a fresh empty `## [Unreleased]` heading above it.
   - Update the compare links at the bottom of the file:

     ```text
     [Unreleased]: https://github.com/millsymills-com/shortcut-mcp/compare/vX.Y.Z...HEAD
     [X.Y.Z]: https://github.com/millsymills-com/shortcut-mcp/compare/vPREV...vX.Y.Z
     ```

4. **Open a release PR** with the `pyproject.toml` + `CHANGELOG.md` changes.
   `main` is protected, so this merges (squash) like any other change. CI,
   including `release-install-smoke`, must pass.

5. **Tag the merged commit** on `main`. Tags are protected and the ruleset
   requires signed commits, so the tag must be signed and annotated:

   ```bash
   git switch main && git pull
   git tag -s vX.Y.Z -m "vX.Y.Z"
   git push origin vX.Y.Z
   ```

6. **Create the GitHub Release** from the tag, using the changelog section as
   the notes:

   ```bash
   gh release create vX.Y.Z --title vX.Y.Z --notes-file <(awk '/^## \[X.Y.Z\]/{f=1;next} /^## \[/{f=0} f' CHANGELOG.md)
   ```

7. **Verify the release.** The `release-install-smoke` workflow builds the wheel
   and asserts `shortcut_mcp.__version__` is not the dev fallback. Confirm a
   clean install resolves the new version:

   ```bash
   uv tool install --force git+https://github.com/millsymills-com/shortcut-mcp@vX.Y.Z
   python -c "import shortcut_mcp; print(shortcut_mcp.__version__)"  # → X.Y.Z
   ```
