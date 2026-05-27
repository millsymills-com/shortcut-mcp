"""Document read and write tools (CRUD, epic link/unlink, tiptap-load, search)."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from shortcut_mcp.clients.shortcut import _seg
from shortcut_mcp.tools._common import (
    LimitParam,
    destructive_tags,
    get_client,
    get_object,
    read_tags,
    require_destructive,
    require_update_fields,
    require_writes,
    shape_document_summary,
    shape_epic_summary,
    shaped_list,
    write_tags,
)

_MODULE = "document"
_READ_ANN = {"readOnlyHint": True, "openWorldHint": True}
_WRITE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": False}
_DESTRUCTIVE_ANN: dict[str, Any] = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True}


def register(server: FastMCP) -> None:
    @server.tool(
        name="shortcut_list_documents",
        description="List all documents in the workspace (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_documents(ctx: Context, limit: LimitParam = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get("/documents")
        return shaped_list(rows, shape_document_summary, limit=limit)

    @server.tool(
        name="shortcut_get_document",
        description="Fetch one document by ID (full object, including markdown content).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_get_document(ctx: Context, doc_id: str) -> dict[str, Any]:
        return await get_object(ctx, f"/documents/{_seg(doc_id)}")

    @server.tool(
        name="shortcut_list_document_epics",
        description="List the epics linked to a document (summary rows).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_list_document_epics(ctx: Context, doc_id: str, limit: LimitParam = 50) -> dict[str, Any]:
        rows = await get_client(ctx).get(f"/documents/{_seg(doc_id)}/epics")
        return shaped_list(rows, shape_epic_summary, limit=limit)

    @server.tool(
        name="shortcut_load_document_tiptap",
        description="Load a document's content as Tiptap JSON (rich-text editor format).",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_load_document_tiptap(
        ctx: Context, doc_id: str, content_format: str | None = None
    ) -> dict[str, Any]:
        params = {"content_format": content_format} if content_format is not None else None
        raw = await get_client(ctx).get(f"/documents/{_seg(doc_id)}/tiptap-load", params=params)
        if not isinstance(raw, dict):
            raise ToolError(f"tiptap-load returned a {type(raw).__name__}, expected a Tiptap JSON object")
        return raw

    @server.tool(
        name="shortcut_search_documents",
        description="Search documents by title (substring match). Returns shaped summary rows.",
        tags=read_tags(_MODULE),
        annotations=_READ_ANN,
    )
    async def shortcut_search_documents(
        ctx: Context,
        title: str,
        archived: bool | None = None,
        created_by_me: bool | None = None,
        followed_by_me: bool | None = None,
        limit: LimitParam = 25,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"title": title, "page_size": min(limit, 25)}
        if archived is not None:
            params["archived"] = archived
        if created_by_me is not None:
            params["created_by_me"] = created_by_me
        if followed_by_me is not None:
            params["followed_by_me"] = followed_by_me
        page = await get_client(ctx).paginate("/search/documents", params=params, limit=limit)
        return shaped_list(page["data"], shape_document_summary, limit=limit, total=page["total"])

    @server.tool(
        name="shortcut_create_document",
        description="Create a document. content_format defaults to the API default (markdown).",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": False},
    )
    async def shortcut_create_document(
        ctx: Context,
        title: str,
        content: str,
        content_format: str | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {"title": title, "content": content}
        if content_format is not None:
            body["content_format"] = content_format
        return await get_client(ctx).post("/documents", json=body)

    @server.tool(
        name="shortcut_update_document",
        description="Update a document's title, content, or content_format.",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_update_document(
        ctx: Context,
        doc_id: str,
        title: str | None = None,
        content: str | None = None,
        content_format: str | None = None,
    ) -> dict[str, Any]:
        require_writes(ctx)
        body: dict[str, Any] = {}
        if title is not None:
            body["title"] = title
        if content is not None:
            body["content"] = content
        if content_format is not None:
            body["content_format"] = content_format
        require_update_fields(body)
        result = await get_client(ctx).put(f"/documents/{_seg(doc_id)}", json=body)
        return result if result is not None else {"id": doc_id}

    @server.tool(
        name="shortcut_link_document_to_epic",
        description="Link a document to an epic (reversible association).",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_link_document_to_epic(ctx: Context, doc_id: str, epic_id: int) -> dict[str, Any]:
        require_writes(ctx)
        result = await get_client(ctx).put(f"/documents/{_seg(doc_id)}/epics/{_seg(str(epic_id))}", json={})
        return result if result is not None else {"doc_id": doc_id, "epic_id": epic_id, "linked": True}

    @server.tool(
        name="shortcut_unlink_document_from_epic",
        description="Remove the link between a document and an epic (reversible; neither is deleted).",
        tags=write_tags(_MODULE),
        annotations={**_WRITE_ANN, "idempotentHint": True},
    )
    async def shortcut_unlink_document_from_epic(ctx: Context, doc_id: str, epic_id: int) -> dict[str, Any]:
        require_writes(ctx)
        await get_client(ctx).delete(f"/documents/{_seg(doc_id)}/epics/{_seg(str(epic_id))}")
        return {"doc_id": doc_id, "epic_id": epic_id, "linked": False}

    @server.tool(
        name="shortcut_delete_document",
        description=(
            "Permanently delete a document. Irreversible. "
            "Requires SHORTCUT_MODE=readwrite and SHORTCUT_ALLOW_DESTRUCTIVE=true."
        ),
        tags=destructive_tags(_MODULE),
        annotations=_DESTRUCTIVE_ANN,
    )
    async def shortcut_delete_document(ctx: Context, doc_id: str) -> dict[str, Any]:
        require_destructive(ctx)
        await get_client(ctx).delete(f"/documents/{_seg(doc_id)}")
        return {"id": doc_id, "deleted": True}
