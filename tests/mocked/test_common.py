from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from shortcut_mcp.config import ShortcutConfig
from shortcut_mcp.server import ServerContext
from shortcut_mcp.tools._common import (
    read_tags,
    require_destructive,
    require_writes,
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


def test_shaped_list_truncates_and_reports():
    rows = [{"id": i, "name": f"s{i}", "extra": "drop"} for i in range(5)]
    out = shaped_list(rows, lambda r: {"id": r["id"], "name": r["name"]}, limit=3, total=99)
    assert out["truncated"] is True
    assert out["total"] == 99
    assert len(out["items"]) == 3
    assert out["items"][0] == {"id": 0, "name": "s0"}
