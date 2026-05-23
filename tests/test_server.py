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


@pytest.mark.asyncio
@respx.mock
async def test_allowlist_excluding_story_hides_get_story(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastmcp import Client

    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_TOOLS", "search")  # story not in allowlist
    respx.get("https://api.app.shortcut.com/api/v3/member").mock(
        return_value=httpx.Response(200, json={"id": "u1", "name": "tester"})
    )
    server = create_server()
    async with Client(server) as client:
        names = {t.name for t in await client.list_tools()}
    assert "shortcut_get_story" not in names


@pytest.mark.asyncio
@respx.mock
async def test_default_profile_includes_story(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastmcp import Client

    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get("https://api.app.shortcut.com/api/v3/member").mock(
        return_value=httpx.Response(200, json={"id": "u1", "name": "tester"})
    )
    server = create_server()
    async with Client(server) as client:
        names = {t.name for t in await client.list_tools()}
    assert "shortcut_get_story" in names  # core profile includes story


@pytest.mark.asyncio
@respx.mock
async def test_all_profile_exposes_full_read_surface(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastmcp import Client

    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get("https://api.app.shortcut.com/api/v3/member").mock(
        return_value=httpx.Response(200, json={"id": "u1", "name": "tester"})
    )
    expected = {
        "shortcut_get_current_member",
        "shortcut_get_epic",
        "shortcut_get_epic_comment",
        "shortcut_get_epic_workflow",
        "shortcut_get_file",
        "shortcut_get_group",
        "shortcut_get_iteration",
        "shortcut_get_label",
        "shortcut_get_linked_file",
        "shortcut_get_member",
        "shortcut_get_objective",
        "shortcut_get_project",
        "shortcut_get_story",
        "shortcut_get_story_comment",
        "shortcut_get_story_link",
        "shortcut_get_story_task",
        "shortcut_get_workflow",
        "shortcut_list_epic_comments",
        "shortcut_list_epic_stories",
        "shortcut_list_epics",
        "shortcut_list_files",
        "shortcut_list_group_stories",
        "shortcut_list_groups",
        "shortcut_list_iteration_stories",
        "shortcut_list_iterations",
        "shortcut_list_label_epics",
        "shortcut_list_label_stories",
        "shortcut_list_labels",
        "shortcut_list_linked_files",
        "shortcut_list_members",
        "shortcut_list_objective_epics",
        "shortcut_list_objectives",
        "shortcut_list_project_stories",
        "shortcut_list_projects",
        "shortcut_list_story_comments",
        "shortcut_list_story_history",
        "shortcut_list_workflows",
        "shortcut_query_stories",
        "shortcut_search",
        "shortcut_search_epics",
        "shortcut_search_iterations",
        "shortcut_search_objectives",
        "shortcut_search_stories",
    }
    server = create_server()
    async with Client(server) as client:
        names = {t.name for t in await client.list_tools()}
    assert names == expected


@pytest.mark.asyncio
@respx.mock
async def test_create_story_hidden_in_readonly_visible_in_readwrite(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastmcp import Client

    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    # Default mode is readonly — create_story must not appear in the tool list.
    respx.get("https://api.app.shortcut.com/api/v3/member").mock(
        return_value=httpx.Response(200, json={"id": "u1", "name": "tester"})
    )
    readonly_server = create_server()
    async with Client(readonly_server) as client:
        readonly_names = {t.name for t in await client.list_tools()}
    assert "shortcut_create_story" not in readonly_names

    # With SHORTCUT_MODE=readwrite it must appear.
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get("https://api.app.shortcut.com/api/v3/member").mock(
        return_value=httpx.Response(200, json={"id": "u1", "name": "tester"})
    )
    readwrite_server = create_server()
    async with Client(readwrite_server) as client:
        readwrite_names = {t.name for t in await client.list_tools()}
    assert "shortcut_create_story" in readwrite_names


@pytest.mark.asyncio
@respx.mock
async def test_core_profile_is_smaller_than_all(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastmcp import Client

    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    respx.get("https://api.app.shortcut.com/api/v3/member").mock(
        return_value=httpx.Response(200, json={"id": "u1", "name": "tester"})
    )
    core_server = create_server()
    async with Client(core_server) as c:
        core_names = {t.name for t in await c.list_tools()}

    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    all_server = create_server()
    async with Client(all_server) as c:
        all_names = {t.name for t in await c.list_tools()}

    assert core_names < all_names  # strict subset
    assert "shortcut_list_projects" in all_names
    assert "shortcut_list_projects" not in core_names
