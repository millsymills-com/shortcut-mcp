"""Tests for create_server() and the lifespan's degraded-yield behavior.

FastMCP 3.3.1 API notes (verified against the installed package):
- Disabled tags are tracked via server.transforms (list of Visibility objects),
  not via _disabled_tags (which does not exist in this version).
- The lifespan callable is at server._lifespan and is invoked as
  server._lifespan(server) -> async context manager yielding the user context.
  There is no run_lifespan() method.
"""

from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp.server.transforms import Visibility

from shortcut_mcp.config import ShortcutConfig
from shortcut_mcp.server import create_server


def _disabled_tags(server) -> set[str]:  # type: ignore[no-untyped-def]
    """Extract all tags that have been disabled on the server via disable()."""
    tags: set[str] = set()
    for t in server.transforms:
        if isinstance(t, Visibility) and not t._enabled and t.tags:
            tags.update(t.tags)
    return tags


def test_create_server_returns_named_fastmcp_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    server = create_server()
    assert server.name == "shortcut-mcp"


def test_server_in_readonly_disables_write_and_destructive_tags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    server = create_server()
    disabled = _disabled_tags(server)
    assert "write" in disabled
    assert "destructive" in disabled


def test_server_in_readwrite_keeps_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    server = create_server()
    disabled = _disabled_tags(server)
    assert "write" not in disabled
    assert "destructive" in disabled  # allow-destructive still false


@pytest.mark.asyncio
@respx.mock
async def test_lifespan_disables_all_tools_on_auth_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "bad")
    respx.get("https://api.app.shortcut.com/api/v3/member").mock(
        return_value=httpx.Response(401, json={"message": "Unauthorized"})
    )
    config = ShortcutConfig()
    server = create_server(config)
    async with server._lifespan(server) as ctx:
        # auth failed → kill switch tripped, all shortcut-tagged tools hidden
        assert "shortcut" in _disabled_tags(server)
        assert ctx.client is None


@pytest.mark.asyncio
@respx.mock
async def test_lifespan_keeps_client_on_successful_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "good")
    respx.get("https://api.app.shortcut.com/api/v3/member").mock(
        return_value=httpx.Response(200, json={"id": "user-123", "name": "tester"})
    )
    server = create_server()
    async with server._lifespan(server) as ctx:
        assert "shortcut" not in _disabled_tags(server)
        assert ctx.client is not None


def test_lifespan_disables_all_when_token_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """No token → no validation attempted, but kill switch must trip."""
    monkeypatch.delenv("SHORTCUT_API_TOKEN", raising=False)
    server = create_server()
    # Built without auth: registration completes but shortcut tag disabled.
    assert "shortcut" in _disabled_tags(server)
