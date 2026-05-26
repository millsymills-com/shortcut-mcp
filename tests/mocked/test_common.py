from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from shortcut_mcp.config import ShortcutConfig
from shortcut_mcp.server import ServerContext
from shortcut_mcp.tools._common import (
    read_tags,
    require_destructive,
    require_update_fields,
    require_writes,
    shape_member_summary,
    shape_story_summary,
    shaped_list,
)


class _StubCtx:
    def __init__(self, config: ShortcutConfig) -> None:
        self.lifespan_context = ServerContext(config=config)


def _cfg(monkeypatch: pytest.MonkeyPatch, **env) -> ShortcutConfig:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return ShortcutConfig()


def test_read_tags_includes_module_and_read(monkeypatch):
    assert read_tags("epic") == {"shortcut", "read", "mod:epic"}


def test_require_writes_blocks_in_readonly(monkeypatch):
    ctx = _StubCtx(_cfg(monkeypatch, SHORTCUT_MODE="readonly"))
    with pytest.raises(ToolError, match="mode_denied"):
        require_writes(ctx)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


def test_require_writes_allows_in_readwrite(monkeypatch):
    ctx = _StubCtx(_cfg(monkeypatch, SHORTCUT_MODE="readwrite"))
    require_writes(ctx)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


def test_require_destructive_blocks_without_flag(monkeypatch):
    ctx = _StubCtx(_cfg(monkeypatch, SHORTCUT_MODE="readwrite"))
    with pytest.raises(ToolError, match="mode_denied"):
        require_destructive(ctx)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


def test_require_destructive_allows_when_enabled(monkeypatch):
    ctx = _StubCtx(_cfg(monkeypatch, SHORTCUT_MODE="readwrite", SHORTCUT_ALLOW_DESTRUCTIVE="true"))
    require_destructive(ctx)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


def test_require_update_fields_blocks_empty_body():
    with pytest.raises(ToolError, match="at least one field"):
        require_update_fields({})


def test_require_update_fields_allows_nonempty_body():
    require_update_fields({"name": "x"})  # no raise


def test_shaped_list_truncates_and_reports():
    rows = [{"id": i, "name": f"s{i}", "extra": "drop"} for i in range(5)]
    out = shaped_list(rows, lambda r: {"id": r["id"], "name": r["name"]}, limit=3, total=99)
    assert out["truncated"] is True
    assert out["total"] == 99
    assert len(out["items"]) == 3
    assert out["items"][0] == {"id": 0, "name": "s0"}


def test_shape_story_summary_picks_key_fields():
    raw = {
        "id": 1,
        "name": "S",
        "story_type": "feature",
        "workflow_state_id": 5,
        "epic_id": 9,
        "archived": False,
        "description": "x" * 9999,
    }
    out = shape_story_summary(raw)
    assert out == {
        "id": 1,
        "name": "S",
        "story_type": "feature",
        "workflow_state_id": 5,
        "epic_id": 9,
        "archived": False,
    }


def test_shape_member_summary_flattens_profile():
    raw = {"id": "m1", "disabled": False, "profile": {"name": "Ada", "mention_name": "ada", "email_address": "a@b.c"}}
    out = shape_member_summary(raw)
    assert out == {"id": "m1", "disabled": False, "name": "Ada", "mention_name": "ada", "email_address": "a@b.c"}


def test_shapers_tolerate_missing_optional_fields():
    assert shape_story_summary({"id": 2})["id"] == 2  # no KeyError
    assert shape_member_summary({"id": "m2"})["id"] == "m2"


def test_shaped_list_drops_rows_with_no_recognized_fields():
    rows = [{"id": 1, "name": "keep"}, {"unknown": "x"}, {"id": 3, "name": "also"}]
    out = shaped_list(rows, shape_story_summary, limit=10, total=3)
    assert [r["id"] for r in out["items"]] == [1, 3]
    assert out["total"] == 3  # total reflects the API count, not the post-filter length


def test_shaped_list_empty_page_is_not_truncated():
    out = shaped_list([], shape_story_summary, limit=10)
    assert out == {"items": [], "truncated": False}


def test_shaped_list_rejects_none():
    with pytest.raises(ToolError, match="expected a list"):
        shaped_list(None, lambda r: r, limit=10)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
