"""Contract tests: replay recorded Shortcut payloads and assert the shape the
client and tool shapers depend on.

Each test pins one representative endpoint. If Shortcut changes a payload,
re-recording surfaces the drift and these assertions document exactly which
fields downstream code relies on (see ``tools/_common.py`` shapers).
"""

from __future__ import annotations

import os

import pytest

from shortcut_mcp.clients.shortcut import ShortcutClient

pytestmark = [pytest.mark.contract, pytest.mark.vcr, pytest.mark.asyncio]


def _token() -> str:
    """Real token authenticates during recording; on replay VCR matches by
    method+URI, so any value works and the token never touches the network."""
    return os.environ.get("SHORTCUT_API_TOKEN", "DUMMY")


async def test_workflows_contract() -> None:
    async with ShortcutClient(token=_token()) as client:
        workflows = await client.get("/workflows")
    assert isinstance(workflows, list), "expected a bare list from /workflows"
    assert workflows, "workspace has no workflows"
    workflow = workflows[0]
    assert {"id", "name", "default_state_id", "states"} <= workflow.keys()
    assert isinstance(workflow["states"], list)
    assert workflow["states"], "workflow has no states"
    assert {"id", "name", "type"} <= workflow["states"][0].keys()


async def test_epics_contract() -> None:
    async with ShortcutClient(token=_token()) as client:
        epics = await client.get("/epics")
    assert isinstance(epics, list), "expected a bare list from /epics"
    assert epics, "workspace has no epics"
    assert {"id", "name"} <= epics[0].keys()


async def test_labels_contract() -> None:
    async with ShortcutClient(token=_token()) as client:
        labels = await client.get("/labels")
    assert isinstance(labels, list), "expected a bare list from /labels"
    assert labels, "workspace has no labels"
    assert {"id", "name"} <= labels[0].keys()


async def test_members_nest_profile_fields() -> None:
    async with ShortcutClient(token=_token()) as client:
        members = await client.get("/members")
    assert isinstance(members, list)
    assert members, "workspace has no members"
    member = members[0]
    assert "id" in member
    profile = member["profile"]
    assert {"name", "mention_name"} <= profile.keys(), "member fields nest under 'profile'"


async def test_member_self_contract() -> None:
    async with ShortcutClient(token=_token()) as client:
        member = await client.get("/member")
    assert "id" in member, "GET /member backs validate_connection()"


async def test_search_stories_returns_data_envelope() -> None:
    async with ShortcutClient(token=_token()) as client:
        page = await client.get("/search/stories", params={"query": "is:story", "page_size": 5})
    assert isinstance(page, dict), "/search/stories returns an object envelope, not a bare list"
    assert isinstance(page.get("data"), list)
    assert "total" in page, "paginate() reads the 'total' field from the search envelope"


async def test_paginate_follows_search_cursor() -> None:
    async with ShortcutClient(token=_token()) as client:
        result = await client.paginate(
            "/search/stories",
            params={"query": "is:story", "page_size": 2},
            max_pages=2,
            limit=3,
        )
    assert set(result) == {"data", "total", "pages"}
    assert len(result["data"]) <= 3


async def test_story_contract() -> None:
    async with ShortcutClient(token=_token()) as client:
        page = await client.get("/search/stories", params={"query": "is:story", "page_size": 1})
        stories = page["data"]
        if not stories:
            pytest.skip("workspace has no stories to fetch")
        story_id = stories[0]["id"]
        story = await client.get(f"/stories/{story_id}")
    assert story["id"] == story_id
    assert {"name", "story_type", "workflow_state_id", "app_url"} <= story.keys()
