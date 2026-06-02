"""Mocked tests for story read and write tools.

FastMCP 3.3.1 invocation pattern (discovered in Task 13):
- `await server.get_tool(name)` returns a FunctionTool (it's async).
- `tool.fn` is the underlying coroutine function, but ctx is dependency-injected
  and cannot be constructed in isolation.
- The correct test pattern is `async with Client(server) as client:` which wires
  up the lifespan and injects ctx properly, then `result = await client.call_tool(name, args)`
  where `result.data` is the return value and `result.is_error` signals an error.
- For error propagation, the MCP surface serializes tool exceptions as error text.
  We verify ShortcutClientError reaches the caller by asserting `result.is_error`.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"


def _mock_member() -> None:
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "user-1"}))


@pytest.mark.asyncio
@respx.mock
async def test_get_story_returns_story_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    _mock_member()
    respx.get(f"{BASE}/stories/1234").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 1234,
                "name": "Tracer bullet",
                "app_url": "https://app.shortcut.com/x/story/1234",
                "workflow_state_id": 500,
            },
        )
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_story", {"story_id": 1234})
    assert not result.is_error
    assert result.data["id"] == 1234
    assert result.data["name"] == "Tracer bullet"


@pytest.mark.asyncio
@respx.mock
async def test_get_story_propagates_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    _mock_member()
    respx.get(f"{BASE}/stories/9999").mock(return_value=httpx.Response(404, json={"message": "not found"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_story", {"story_id": 9999}, raise_on_error=False)
    assert result.is_error
    assert "404" in result.content[0].text


@pytest.mark.asyncio
@respx.mock
async def test_get_story_raises_on_empty_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    _mock_member()
    respx.get(f"{BASE}/stories/1234").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_story", {"story_id": 1234}, raise_on_error=False)
    assert result.is_error
    assert "empty body" in result.content[0].text.lower()


@pytest.mark.asyncio
@respx.mock
async def test_get_story_raises_on_non_dict_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    _mock_member()
    respx.get(f"{BASE}/stories/1234").mock(return_value=httpx.Response(200, json=[{"id": 1234}]))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_get_story", {"story_id": 1234}, raise_on_error=False)
    assert result.is_error
    assert "expected a single object" in result.content[0].text.lower()


@pytest.mark.asyncio
@respx.mock
async def test_list_story_history_returns_items(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    _mock_member()
    respx.get(f"{BASE}/stories/7/history").mock(return_value=httpx.Response(200, json=[{"id": "h1"}, {"id": "h2"}]))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_story_history", {"story_id": 7})
    assert not result.is_error
    assert result.data["items"][0]["id"] == "h1"
    assert result.data["truncated"] is False


@pytest.mark.asyncio
@respx.mock
async def test_list_story_sub_tasks_shapes_child_stories(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    _mock_member()
    respx.get(f"{BASE}/stories/7/sub-tasks").mock(
        return_value=httpx.Response(200, json=[{"id": 8, "name": "child", "story_type": "feature", "drop": 1}])
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_story_sub_tasks", {"story_id": 7})
    assert not result.is_error
    assert result.data["items"][0] == {"id": 8, "name": "child", "story_type": "feature"}


# ---------------------------------------------------------------------------
# Write tool tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_create_story_posts_and_returns_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    _mock_member()
    route = respx.post(f"{BASE}/stories").mock(return_value=httpx.Response(201, json={"id": 1, "name": "S"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_create_story", {"name": "S", "workflow_state_id": 500})
    assert not result.is_error
    assert result.data["id"] == 1
    body = json.loads(route.calls.last.request.content)
    assert body["name"] == "S"
    assert body["workflow_state_id"] == 500


@pytest.mark.asyncio
@respx.mock
async def test_create_story_includes_optional_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    _mock_member()
    route = respx.post(f"{BASE}/stories").mock(return_value=httpx.Response(201, json={"id": 2, "name": "T"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_create_story",
            {
                "name": "T",
                "workflow_state_id": 500,
                "labels": ["bug", "backend"],
                "owner_ids": ["u1"],
            },
        )
    assert not result.is_error
    body = json.loads(route.calls.last.request.content)
    assert body["labels"] == [{"name": "bug"}, {"name": "backend"}]
    assert body["owner_ids"] == ["u1"]


@pytest.mark.asyncio
@respx.mock
async def test_update_story_returns_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    _mock_member()
    respx.put(f"{BASE}/stories/5").mock(return_value=httpx.Response(200, json={"id": 5}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_story", {"story_id": 5, "name": "Updated"})
    assert not result.is_error
    assert result.data["id"] == 5


@pytest.mark.asyncio
@respx.mock
async def test_update_story_sets_external_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    _mock_member()
    route = respx.put(f"{BASE}/stories/5").mock(return_value=httpx.Response(200, json={"id": 5}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_story", {"story_id": 5, "external_id": "repo#42"})
    assert not result.is_error
    body = json.loads(route.calls.last.request.content)
    assert body["external_id"] == "repo#42"


@pytest.mark.asyncio
@respx.mock
async def test_update_story_tolerates_empty_put_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    _mock_member()
    respx.put(f"{BASE}/stories/5").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_story", {"story_id": 5, "name": "Updated"})
    assert not result.is_error
    assert result.data["id"] == 5


@pytest.mark.asyncio
@respx.mock
async def test_archive_story_sends_archived_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    _mock_member()
    route = respx.put(f"{BASE}/stories/10").mock(return_value=httpx.Response(200, json={"id": 10, "archived": True}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_archive_story", {"story_id": 10})
    assert not result.is_error
    body = json.loads(route.calls.last.request.content)
    assert body == {"archived": True}


@pytest.mark.asyncio
@respx.mock
async def test_unarchive_story_sends_archived_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    _mock_member()
    route = respx.put(f"{BASE}/stories/10").mock(return_value=httpx.Response(200, json={"id": 10, "archived": False}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_unarchive_story", {"story_id": 10})
    assert not result.is_error
    body = json.loads(route.calls.last.request.content)
    assert body == {"archived": False}


@pytest.mark.asyncio
@respx.mock
async def test_add_story_labels_merges_and_dedupes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    _mock_member()
    respx.get(f"{BASE}/stories/5").mock(
        return_value=httpx.Response(200, json={"id": 5, "labels": [{"name": "a"}], "owner_ids": ["u1"]})
    )
    put_route = respx.put(f"{BASE}/stories/5").mock(return_value=httpx.Response(200, json={"id": 5}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_add_story_labels", {"story_id": 5, "labels": ["b"]})
    assert not result.is_error
    body = json.loads(put_route.calls.last.request.content)
    assert body["labels"] == [{"name": "a"}, {"name": "b"}]


@pytest.mark.asyncio
@respx.mock
async def test_add_story_labels_dedupes_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    _mock_member()
    respx.get(f"{BASE}/stories/5").mock(
        return_value=httpx.Response(200, json={"id": 5, "labels": [{"name": "a"}, {"name": "b"}], "owner_ids": []})
    )
    put_route = respx.put(f"{BASE}/stories/5").mock(return_value=httpx.Response(200, json={"id": 5}))
    server = create_server()
    async with Client(server) as client:
        await client.call_tool("shortcut_add_story_labels", {"story_id": 5, "labels": ["a", "c"]})
    body = json.loads(put_route.calls.last.request.content)
    assert body["labels"] == [{"name": "a"}, {"name": "b"}, {"name": "c"}]


@pytest.mark.asyncio
@respx.mock
async def test_add_story_owners_merges_and_dedupes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    _mock_member()
    respx.get(f"{BASE}/stories/5").mock(
        return_value=httpx.Response(200, json={"id": 5, "labels": [], "owner_ids": ["u1"]})
    )
    put_route = respx.put(f"{BASE}/stories/5").mock(return_value=httpx.Response(200, json={"id": 5}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_add_story_owners", {"story_id": 5, "owner_ids": ["u2", "u1"]})
    assert not result.is_error
    body = json.loads(put_route.calls.last.request.content)
    assert body["owner_ids"] == ["u1", "u2"]


@pytest.mark.asyncio
@respx.mock
async def test_bulk_create_stories_posts_stories_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    _mock_member()
    route = respx.post(f"{BASE}/stories/bulk").mock(return_value=httpx.Response(201, json=[{"id": 1}, {"id": 2}]))
    server = create_server()
    stories = [{"name": "S1", "workflow_state_id": 500}, {"name": "S2", "workflow_state_id": 500}]
    async with Client(server) as client:
        result = await client.call_tool("shortcut_bulk_create_stories", {"stories": stories})
    assert not result.is_error
    body = json.loads(route.calls.last.request.content)
    assert body == {"stories": stories}


@pytest.mark.asyncio
@respx.mock
async def test_bulk_update_stories_includes_only_provided_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    _mock_member()
    route = respx.put(f"{BASE}/stories/bulk").mock(return_value=httpx.Response(200, json=[{"id": 1}]))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_bulk_update_stories",
            {"story_ids": [1, 2], "workflow_state_id": 600},
        )
    assert not result.is_error
    body = json.loads(route.calls.last.request.content)
    assert body["story_ids"] == [1, 2]
    assert body["workflow_state_id"] == 600
    assert "archived" not in body
    assert "epic_id" not in body


@pytest.mark.asyncio
@respx.mock
async def test_create_story_from_template_includes_template_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    _mock_member()
    route = respx.post(f"{BASE}/stories/from-template").mock(
        return_value=httpx.Response(201, json={"id": 99, "name": "From template"})
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_create_story_from_template",
            {"template_id": "tmpl-abc", "name": "Override name"},
        )
    assert not result.is_error
    assert result.data["id"] == 99
    body = json.loads(route.calls.last.request.content)
    assert body["story_template_id"] == "tmpl-abc"
    assert body["name"] == "Override name"


@pytest.mark.asyncio
@respx.mock
async def test_create_story_denied_in_readonly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    # SHORTCUT_MODE defaults to readonly — no setenv needed
    _mock_member()
    server = create_server()
    # Re-enable the tag the visibility gate stripped, so the call reaches the
    # in-body require_writes() guard instead of failing at "unknown tool".
    server.enable(tags={"write"})
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_create_story",
            {"name": "S", "workflow_state_id": 500},
            raise_on_error=False,
        )
    assert result.is_error
    assert "mode_denied" in result.content[0].text


@pytest.mark.asyncio
@respx.mock
async def test_delete_story_calls_delete_and_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/stories/7").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_story", {"story_id": 7})
    assert not result.is_error
    assert result.data == {"id": 7, "deleted": True}
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_bulk_delete_stories_sends_ids_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/stories/bulk").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_bulk_delete_stories", {"story_ids": [1, 2, 3]})
    assert not result.is_error
    assert result.data == {"story_ids": [1, 2, 3], "deleted": True}
    body = json.loads(route.calls.last.request.content)
    assert body == {"story_ids": [1, 2, 3]}


@pytest.mark.asyncio
@respx.mock
async def test_delete_story_hidden_without_destructive_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")  # writes on, destructive OFF
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    server = create_server()
    async with Client(server) as client:
        names = {t.name for t in await client.list_tools()}
    assert "shortcut_delete_story" not in names


@pytest.mark.asyncio
@respx.mock
async def test_update_story_with_no_fields_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    put_route = respx.put(f"{BASE}/stories/5").mock(return_value=httpx.Response(200, json={"id": 5}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_update_story", {"story_id": 5}, raise_on_error=False)
    assert result.is_error
    assert "at least one field" in result.content[0].text
    assert not put_route.called  # guard raises before any HTTP call
