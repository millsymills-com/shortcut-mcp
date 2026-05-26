"""Every write tool's optional-field branches land in the request body.

Each ``create``/``update`` handler builds its JSON body from a chain of
``if arg is not None`` guards. Calling each tool with all optional args set
exercises those branches and pins the wire shape (e.g. story ``labels`` are
posted as ``[{"name": ...}]``, not bare strings).
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"


def _mock_member() -> None:
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "user-1"}))


_POST_CASES: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = [
    (
        "shortcut_create_story",
        "/stories",
        {
            "name": "S",
            "workflow_state_id": 500,
            "description": "d",
            "epic_id": 9,
            "iteration_id": 7,
            "story_type": "feature",
            "owner_ids": ["u1"],
            "labels": ["bug"],
        },
        {
            "name": "S",
            "workflow_state_id": 500,
            "description": "d",
            "epic_id": 9,
            "iteration_id": 7,
            "story_type": "feature",
            "owner_ids": ["u1"],
            "labels": [{"name": "bug"}],
        },
    ),
    (
        "shortcut_create_story_from_template",
        "/stories/from-template",
        {
            "template_id": "t1",
            "name": "S",
            "description": "d",
            "epic_id": 9,
            "iteration_id": 7,
            "story_type": "bug",
            "owner_ids": ["u1"],
            "labels": ["x"],
        },
        {
            "story_template_id": "t1",
            "name": "S",
            "description": "d",
            "epic_id": 9,
            "iteration_id": 7,
            "story_type": "bug",
            "owner_ids": ["u1"],
            "labels": [{"name": "x"}],
        },
    ),
    (
        "shortcut_create_epic",
        "/epics",
        {
            "name": "E",
            "description": "d",
            "milestone_id": 3,
            "owner_ids": ["u1"],
            "planned_start_date": "2026-01-01",
            "deadline": "2026-02-01",
        },
        {
            "name": "E",
            "description": "d",
            "milestone_id": 3,
            "owner_ids": ["u1"],
            "planned_start_date": "2026-01-01",
            "deadline": "2026-02-01",
        },
    ),
    (
        "shortcut_create_iteration",
        "/iterations",
        {
            "name": "I",
            "start_date": "2026-01-01",
            "end_date": "2026-01-14",
            "description": "d",
            "group_ids": ["g1"],
        },
        {
            "name": "I",
            "start_date": "2026-01-01",
            "end_date": "2026-01-14",
            "description": "d",
            "group_ids": ["g1"],
        },
    ),
    (
        "shortcut_create_label",
        "/labels",
        {"name": "L", "color": "#fff", "description": "d"},
        {"name": "L", "color": "#fff", "description": "d"},
    ),
    (
        "shortcut_create_objective",
        "/objectives",
        {"name": "O", "description": "d", "state": "in progress"},
        {"name": "O", "description": "d", "state": "in progress"},
    ),
    (
        "shortcut_create_project",
        "/projects",
        {"name": "P", "team_id": 4, "description": "d", "color": "#000"},
        {"name": "P", "team_id": 4, "description": "d", "color": "#000"},
    ),
    (
        "shortcut_create_group",
        "/groups",
        {"name": "G", "mention_name": "g", "description": "d", "member_ids": ["u1"]},
        {"name": "G", "mention_name": "g", "description": "d", "member_ids": ["u1"]},
    ),
    (
        "shortcut_create_linked_file",
        "/linked-files",
        {"name": "F", "url": "https://x", "type": "google", "description": "d", "story_id": 5},
        {"name": "F", "url": "https://x", "type": "google", "description": "d", "story_id": 5},
    ),
]


_PUT_CASES: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = [
    (
        "shortcut_update_story",
        "/stories/5",
        {
            "story_id": 5,
            "name": "S",
            "description": "d",
            "workflow_state_id": 500,
            "epic_id": 9,
            "iteration_id": 7,
            "story_type": "feature",
            "archived": True,
            "owner_ids": ["u1"],
            "labels": ["bug"],
        },
        {
            "name": "S",
            "description": "d",
            "workflow_state_id": 500,
            "epic_id": 9,
            "iteration_id": 7,
            "story_type": "feature",
            "archived": True,
            "owner_ids": ["u1"],
            "labels": [{"name": "bug"}],
        },
    ),
    (
        "shortcut_bulk_update_stories",
        "/stories/bulk",
        {"story_ids": [1, 2], "archived": True, "workflow_state_id": 500, "epic_id": 9, "iteration_id": 7},
        {"story_ids": [1, 2], "archived": True, "workflow_state_id": 500, "epic_id": 9, "iteration_id": 7},
    ),
    (
        "shortcut_update_epic",
        "/epics/5",
        {
            "epic_id": 5,
            "name": "E",
            "description": "d",
            "epic_state_id": 2,
            "milestone_id": 3,
            "owner_ids": ["u1"],
            "deadline": "2026-02-01",
        },
        {
            "name": "E",
            "description": "d",
            "epic_state_id": 2,
            "milestone_id": 3,
            "owner_ids": ["u1"],
            "deadline": "2026-02-01",
        },
    ),
    (
        "shortcut_update_iteration",
        "/iterations/5",
        {"iteration_id": 5, "name": "I", "start_date": "2026-01-01", "end_date": "2026-01-14", "description": "d"},
        {"name": "I", "start_date": "2026-01-01", "end_date": "2026-01-14", "description": "d"},
    ),
    (
        "shortcut_update_label",
        "/labels/5",
        {"label_id": 5, "name": "L", "color": "#fff", "description": "d", "archived": True},
        {"name": "L", "color": "#fff", "description": "d", "archived": True},
    ),
    (
        "shortcut_update_objective",
        "/objectives/5",
        {"objective_id": 5, "name": "O", "description": "d", "state": "done"},
        {"name": "O", "description": "d", "state": "done"},
    ),
    (
        "shortcut_update_project",
        "/projects/5",
        {"project_id": 5, "name": "P", "description": "d", "color": "#000", "archived": True},
        {"name": "P", "description": "d", "color": "#000", "archived": True},
    ),
    (
        "shortcut_update_group",
        "/groups/g1",
        {
            "group_id": "g1",
            "name": "G",
            "mention_name": "g",
            "description": "d",
            "member_ids": ["u1"],
            "archived": True,
        },
        {"name": "G", "mention_name": "g", "description": "d", "member_ids": ["u1"], "archived": True},
    ),
    (
        "shortcut_update_linked_file",
        "/linked-files/5",
        {"linked_file_id": 5, "name": "F", "url": "https://x", "type": "google", "description": "d"},
        {"name": "F", "url": "https://x", "type": "google", "description": "d"},
    ),
    (
        "shortcut_update_file",
        "/files/5",
        {"file_id": 5, "name": "F", "description": "d"},
        {"name": "F", "description": "d"},
    ),
]


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(("tool", "path", "args", "expected_body"), _POST_CASES)
async def test_create_tool_sends_optional_fields(
    monkeypatch: pytest.MonkeyPatch,
    tool: str,
    path: str,
    args: dict[str, Any],
    expected_body: dict[str, Any],
) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    _mock_member()
    route = respx.post(f"{BASE}{path}").mock(return_value=httpx.Response(201, json={"id": 1}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(tool, args)
    assert not result.is_error
    assert json.loads(route.calls.last.request.content) == expected_body


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(("tool", "path", "args", "expected_body"), _PUT_CASES)
async def test_update_tool_sends_optional_fields(
    monkeypatch: pytest.MonkeyPatch,
    tool: str,
    path: str,
    args: dict[str, Any],
    expected_body: dict[str, Any],
) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    _mock_member()
    body_back: Any = [{"id": 1}] if path.endswith("/bulk") else {"id": 1}
    route = respx.put(f"{BASE}{path}").mock(return_value=httpx.Response(200, json=body_back))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(tool, args)
    assert not result.is_error
    assert json.loads(route.calls.last.request.content) == expected_body
