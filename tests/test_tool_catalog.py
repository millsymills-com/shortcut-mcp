"""The README tool catalog must match the live tool registry."""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_generator():
    path = _REPO_ROOT / "scripts" / "generate_tool_catalog.py"
    spec = importlib.util.spec_from_file_location("generate_tool_catalog", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_gtc = _load_generator()


def test_readme_tool_catalog_is_in_sync() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/generate_tool_catalog.py", "--check"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_splice_raises_for_missing_begin_marker() -> None:
    with pytest.raises(ValueError, match=re.escape(_gtc.BEGIN)):
        _gtc._splice(f"no markers here\n{_gtc.END}\n", "block")


def test_splice_raises_for_missing_end_marker() -> None:
    with pytest.raises(ValueError, match=re.escape(_gtc.END)):
        _gtc._splice(f"{_gtc.BEGIN}\nopen but never closed\n", "block")


def test_splice_replaces_block_between_markers() -> None:
    readme = f"intro\n{_gtc.BEGIN}\nold\n{_gtc.END}\noutro\n"
    spliced = _gtc._splice(readme, "NEW")
    assert "old" not in spliced
    assert "NEW" in spliced
    assert spliced.startswith("intro\n")
    assert spliced.endswith("outro\n")


def test_render_handles_empty_registry() -> None:
    rendered = _gtc._render([])
    assert "### Read tools (0)" in rendered
    assert "### Write tools (0)" in rendered
    assert "### Destructive tools (0)" in rendered
    assert rendered.endswith("\n")


@pytest.mark.parametrize("desc", ["", "   ", None])
def test_rows_fails_fast_on_empty_description(desc: str | None) -> None:
    tools = [SimpleNamespace(name="shortcut_blank", tags={"read", "mod:thing"}, description=desc)]
    with pytest.raises(ValueError, match="shortcut_blank"):
        _gtc._rows(tools)


def test_rows_maps_tier_module_and_strips_description() -> None:
    tools = [SimpleNamespace(name="shortcut_do", tags={"write", "mod:widget"}, description="  Do it.  ")]
    assert _gtc._rows(tools) == [("write", "widget", "shortcut_do", "Do it.")]


def test_rows_maps_destructive_tier() -> None:
    tools = [SimpleNamespace(name="shortcut_nuke", tags={"destructive", "mod:widget"}, description="Nuke it.")]
    assert _gtc._rows(tools) == [("destructive", "widget", "shortcut_nuke", "Nuke it.")]


def test_rows_falls_back_to_other_module_without_mod_tag() -> None:
    tools = [SimpleNamespace(name="shortcut_misc", tags={"read"}, description="Misc.")]
    assert _gtc._rows(tools) == [("read", "other", "shortcut_misc", "Misc.")]
