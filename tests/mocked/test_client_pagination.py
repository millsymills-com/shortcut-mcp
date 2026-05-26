from __future__ import annotations

import httpx
import pytest
import respx
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from shortcut_mcp.clients.shortcut import ShortcutClient, _split_next


def test_split_next_strips_api_prefix_and_query():
    path, params = _split_next("/api/v3/search/stories?token=abc&page_size=25")
    assert path == "/search/stories"
    assert params == {"token": "abc", "page_size": "25"}


def test_split_next_rejects_absolute_url():
    with pytest.raises(ValueError, match="relative"):
        _split_next("https://evil.example/api/v3/search/stories?token=abc")


def test_split_next_rejects_scheme_relative_url():
    with pytest.raises(ValueError, match="relative"):
        _split_next("//evil.example/api/v3/search/stories")


def test_split_next_rejects_no_leading_slash():
    with pytest.raises(ValueError, match="leading slash"):
        _split_next("api/v3/search/stories")


@pytest.mark.asyncio
@respx.mock
async def test_paginate_follows_next_until_exhausted():
    base = "https://api.app.shortcut.com/api/v3"
    page1_next = "/api/v3/search/stories?token=t2"
    respx.get(f"{base}/search/stories", params={"query": "x"}).mock(
        return_value=httpx.Response(200, json={"data": [{"id": 1}], "next": page1_next, "total": 2})
    )
    respx.get(f"{base}/search/stories", params={"token": "t2"}).mock(
        return_value=httpx.Response(200, json={"data": [{"id": 2}], "next": None, "total": 2})
    )
    client = ShortcutClient(token="x")
    page = await client.paginate("/search/stories", params={"query": "x"}, max_pages=5, limit=10)
    await client.close()
    assert [r["id"] for r in page["data"]] == [1, 2]
    assert page["total"] == 2


@pytest.mark.asyncio
@respx.mock
async def test_paginate_total_taken_from_first_page():
    base = "https://api.app.shortcut.com/api/v3"
    page1_next = "/api/v3/search/stories?token=t2"
    respx.get(f"{base}/search/stories", params={"query": "x"}).mock(
        return_value=httpx.Response(200, json={"data": [{"id": 1}], "next": page1_next, "total": 2})
    )
    respx.get(f"{base}/search/stories", params={"token": "t2"}).mock(
        return_value=httpx.Response(200, json={"data": [{"id": 2}], "next": None, "total": 5})
    )
    client = ShortcutClient(token="x")
    page = await client.paginate("/search/stories", params={"query": "x"}, max_pages=5, limit=10)
    await client.close()
    assert page["total"] == 2  # first page's snapshot, not the last page's drifted count


@pytest.mark.asyncio
@respx.mock
async def test_paginate_respects_max_pages():
    base = "https://api.app.shortcut.com/api/v3"
    loop_next = "/api/v3/search/stories?token=loop"
    respx.get(f"{base}/search/stories").mock(
        return_value=httpx.Response(200, json={"data": [{"id": 1}], "next": loop_next, "total": 99})
    )
    client = ShortcutClient(token="x")
    page = await client.paginate("/search/stories", params={"query": "x"}, max_pages=2, limit=1000)
    await client.close()
    assert len(page["data"]) == 2  # stopped after 2 pages despite a perpetual `next`


@pytest.mark.asyncio
@respx.mock
async def test_paginate_rejects_non_dict_page():
    base = "https://api.app.shortcut.com/api/v3"
    respx.get(f"{base}/search/stories").mock(return_value=httpx.Response(200, json=[1, 2, 3]))
    from shortcut_mcp.errors import ShortcutError

    client = ShortcutClient(token="x")
    with pytest.raises(ShortcutError, match="expected a paginated object"):
        await client.paginate("/search/stories", params={"query": "x"})
    await client.close()


def test_split_next_rejects_double_slash():
    with pytest.raises(ValueError, match="scheme-relative"):
        _split_next("/api/v3//evil.com/x")


@pytest.mark.asyncio
@settings(max_examples=25, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(page_count=st.integers(min_value=1, max_value=20), cap=st.integers(min_value=1, max_value=10))
async def test_paginate_never_exceeds_max_pages(page_count: int, cap: int):
    base = "https://api.app.shortcut.com/api/v3"
    with respx.mock:
        prop_next = "/api/v3/search/stories?token=t"
        respx.get(f"{base}/search/stories").mock(
            return_value=httpx.Response(200, json={"data": [{"id": 1}], "next": prop_next, "total": page_count})
        )
        client = ShortcutClient(token="x")
        page = await client.paginate("/search/stories", params={"query": "q"}, max_pages=cap, limit=10_000)
        await client.close()
    assert page["pages"] <= cap
