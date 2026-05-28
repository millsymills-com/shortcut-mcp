from __future__ import annotations

import json

import httpx
import pytest
import respx
from fastmcp import Client

from shortcut_mcp.server import create_server

BASE = "https://api.app.shortcut.com/api/v3"
DOC = "doc-123"


@pytest.mark.asyncio
@respx.mock
async def test_list_documents_shapes_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/documents").mock(
        return_value=httpx.Response(200, json=[{"id": DOC, "title": "Spec", "app_url": "u", "content_markdown": "x"}])
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_list_documents", {})
    assert result.data["items"][0] == {"id": DOC, "title": "Spec", "app_url": "u"}


@pytest.mark.asyncio
@respx.mock
async def test_get_document_and_epics_and_tiptap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/documents/{DOC}").mock(return_value=httpx.Response(200, json={"id": DOC, "title": "Spec"}))
    respx.get(f"{BASE}/documents/{DOC}/epics").mock(return_value=httpx.Response(200, json=[{"id": 5, "name": "E"}]))
    respx.get(f"{BASE}/documents/{DOC}/tiptap-load").mock(
        return_value=httpx.Response(200, json={"type": "doc", "content": []})
    )
    server = create_server()
    async with Client(server) as client:
        got = await client.call_tool("shortcut_get_document", {"doc_id": DOC})
        epics = await client.call_tool("shortcut_list_document_epics", {"doc_id": DOC})
        tiptap = await client.call_tool("shortcut_load_document_tiptap", {"doc_id": DOC})
    assert got.data["id"] == DOC
    assert epics.data["items"][0]["id"] == 5
    assert tiptap.data["type"] == "doc"


@pytest.mark.asyncio
@respx.mock
async def test_search_documents_requires_title_and_shapes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/search/documents").mock(
        return_value=httpx.Response(
            200, json={"data": [{"id": DOC, "title": "Spec", "app_url": "u"}], "total": 1, "next": None}
        )
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_search_documents", {"title": "Spec"})
    assert not result.is_error
    assert result.data["items"][0]["id"] == DOC
    assert result.data["total"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_create_and_update_document(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    post = respx.post(f"{BASE}/documents").mock(return_value=httpx.Response(201, json={"id": DOC}))
    put = respx.put(f"{BASE}/documents/{DOC}").mock(return_value=httpx.Response(200, json={"id": DOC}))
    server = create_server()
    async with Client(server) as client:
        created = await client.call_tool("shortcut_create_document", {"title": "T", "content": "# Hi"})
        updated = await client.call_tool("shortcut_update_document", {"doc_id": DOC, "title": "T2"})
    assert created.data["id"] == DOC
    assert json.loads(post.calls.last.request.content) == {"title": "T", "content": "# Hi"}
    assert json.loads(put.calls.last.request.content) == {"title": "T2"}
    assert updated.data["id"] == DOC


@pytest.mark.asyncio
@respx.mock
async def test_link_and_unlink_document_epic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.put(f"{BASE}/documents/{DOC}/epics/5").mock(return_value=httpx.Response(204))
    respx.delete(f"{BASE}/documents/{DOC}/epics/5").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        linked = await client.call_tool("shortcut_link_document_to_epic", {"doc_id": DOC, "epic_id": 5})
        unlinked = await client.call_tool("shortcut_unlink_document_from_epic", {"doc_id": DOC, "epic_id": 5})
    assert linked.data == {"doc_id": DOC, "epic_id": 5, "linked": True}
    assert unlinked.data == {"doc_id": DOC, "epic_id": 5, "linked": False}


@pytest.mark.asyncio
@respx.mock
async def test_unlink_is_write_tier_not_destructive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    server = create_server()
    async with Client(server) as client:
        names = {t.name for t in await client.list_tools()}
    # Reversible association removal stays in the write tier (no ALLOW_DESTRUCTIVE here).
    assert "shortcut_unlink_document_from_epic" in names
    assert "shortcut_delete_document" not in names


@pytest.mark.asyncio
@respx.mock
async def test_delete_document(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_ALLOW_DESTRUCTIVE", "true")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.delete(f"{BASE}/documents/{DOC}").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_document", {"doc_id": DOC})
    assert result.data == {"id": DOC, "deleted": True}


@pytest.mark.asyncio
@respx.mock
async def test_search_documents_forwards_optional_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.get(f"{BASE}/search/documents").mock(
        return_value=httpx.Response(200, json={"data": [], "total": 0, "next": None})
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_search_documents",
            {"title": "x", "archived": True, "created_by_me": False, "followed_by_me": True},
        )
    assert not result.is_error
    q = dict(route.calls.last.request.url.params)
    assert q["archived"] == "true"
    assert q["created_by_me"] == "false"
    assert q["followed_by_me"] == "true"


@pytest.mark.asyncio
@respx.mock
async def test_tiptap_load_rejects_non_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.get(f"{BASE}/documents/{DOC}/tiptap-load").mock(return_value=httpx.Response(200, json=[1, 2]))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_load_document_tiptap", {"doc_id": DOC}, raise_on_error=False)
    assert result.is_error
    assert "tiptap json object" in result.content[0].text.lower()


@pytest.mark.asyncio
@respx.mock
async def test_create_document_includes_content_format(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    post = respx.post(f"{BASE}/documents").mock(return_value=httpx.Response(201, json={"id": DOC}))
    server = create_server()
    async with Client(server) as client:
        await client.call_tool("shortcut_create_document", {"title": "T", "content": "c", "content_format": "markdown"})
    assert json.loads(post.calls.last.request.content) == {"title": "T", "content": "c", "content_format": "markdown"}


@pytest.mark.asyncio
@respx.mock
async def test_update_document_content_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    put = respx.put(f"{BASE}/documents/{DOC}").mock(return_value=httpx.Response(204))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool(
            "shortcut_update_document", {"doc_id": DOC, "content": "new", "content_format": "markdown"}
        )
    assert result.data == {"id": DOC}
    assert json.loads(put.calls.last.request.content) == {"content": "new", "content_format": "markdown"}


@pytest.mark.asyncio
@respx.mock
async def test_link_document_returns_api_body_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    respx.put(f"{BASE}/documents/{DOC}/epics/5").mock(return_value=httpx.Response(200, json={"id": DOC, "title": "T"}))
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_link_document_to_epic", {"doc_id": DOC, "epic_id": 5})
    assert result.data == {"id": DOC, "title": "T"}


@pytest.mark.asyncio
@respx.mock
async def test_delete_document_runtime_guard_blocks_without_destructive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_MODE", "readwrite")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.delete(f"{BASE}/documents/{DOC}").mock(return_value=httpx.Response(204))
    server = create_server()
    # Re-enable the tag the visibility gate stripped, so the call reaches the
    # in-body require_destructive() guard instead of failing at "unknown tool".
    server.enable(tags={"destructive"})
    async with Client(server) as client:
        result = await client.call_tool("shortcut_delete_document", {"doc_id": DOC}, raise_on_error=False)
    assert result.is_error
    assert "mode_denied" in result.content[0].text
    assert not route.called


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(("limit", "expected_page_size"), [(50, "25"), (10, "10")])
async def test_search_documents_clamps_page_size(
    monkeypatch: pytest.MonkeyPatch, limit: int, expected_page_size: str
) -> None:
    monkeypatch.setenv("SHORTCUT_API_TOKEN", "x")
    monkeypatch.setenv("SHORTCUT_PROFILE", "all")
    respx.get(f"{BASE}/member").mock(return_value=httpx.Response(200, json={"id": "u"}))
    route = respx.get(f"{BASE}/search/documents").mock(
        return_value=httpx.Response(200, json={"data": [], "total": 0, "next": None})
    )
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("shortcut_search_documents", {"title": "x", "limit": limit})
    assert not result.is_error
    assert dict(route.calls.last.request.url.params)["page_size"] == expected_page_size
