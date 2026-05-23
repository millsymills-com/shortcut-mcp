"""Tests for the retry + error-mapping layer.

Critical invariants:
- GET/HEAD on timeout/connection: retried up to max_retries
- POST/PUT/DELETE on timeout/connection: NEVER retried
- 429: NEVER retried, raises ShortcutRateLimitedError
- 5xx: NEVER auto-retried in v0.1
- Each 4xx maps to its typed subclass
"""

from __future__ import annotations

import httpx
import pytest
import respx

from shortcut_mcp.clients.shortcut import ShortcutClient
from shortcut_mcp.errors import (
    ShortcutAuthError,
    ShortcutClientError,
    ShortcutRateLimitedError,
    ShortcutServerError,
    ShortcutTimeoutError,
)


@pytest.mark.asyncio
@respx.mock
async def test_retries_get_on_timeout_then_succeeds() -> None:
    route = respx.get("https://api.app.shortcut.com/api/v3/stories/1").mock(
        side_effect=[
            httpx.TimeoutException("first"),
            httpx.Response(200, json={"id": 1}),
        ]
    )
    async with ShortcutClient(token="x", max_retries=3) as client:
        result = await client.get("/stories/1")
    assert result == {"id": 1}
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_get_timeout_exhausts_retries_then_raises() -> None:
    route = respx.get("https://api.app.shortcut.com/api/v3/stories/1").mock(
        side_effect=httpx.TimeoutException("always")
    )
    async with ShortcutClient(token="x", max_retries=2) as client:
        with pytest.raises(ShortcutTimeoutError):
            await client.get("/stories/1")
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_post_timeout_does_not_retry() -> None:
    route = respx.post("https://api.app.shortcut.com/api/v3/stories").mock(side_effect=httpx.TimeoutException("once"))
    async with ShortcutClient(token="x", max_retries=3) as client:
        with pytest.raises(ShortcutTimeoutError):
            await client.post("/stories", json={"name": "x"})
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_429_raises_rate_limited_and_does_not_retry() -> None:
    route = respx.get("https://api.app.shortcut.com/api/v3/stories/1").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "30"}, json={"message": "slow"})
    )
    async with ShortcutClient(token="x", max_retries=3) as client:
        with pytest.raises(ShortcutRateLimitedError) as info:
            await client.get("/stories/1")
    assert route.call_count == 1
    assert info.value.retry_after == 30.0


@pytest.mark.asyncio
@respx.mock
async def test_500_does_not_auto_retry() -> None:
    route = respx.get("https://api.app.shortcut.com/api/v3/stories/1").mock(
        return_value=httpx.Response(500, json={"message": "boom"})
    )
    async with ShortcutClient(token="x", max_retries=3) as client:
        with pytest.raises(ShortcutServerError):
            await client.get("/stories/1")
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_401_raises_auth_error() -> None:
    respx.get("https://api.app.shortcut.com/api/v3/stories/1").mock(
        return_value=httpx.Response(401, json={"message": "Unauthorized"})
    )
    async with ShortcutClient(token="bad") as client:
        with pytest.raises(ShortcutAuthError):
            await client.get("/stories/1")


@pytest.mark.asyncio
@respx.mock
async def test_404_raises_client_error() -> None:
    respx.get("https://api.app.shortcut.com/api/v3/stories/9999").mock(
        return_value=httpx.Response(404, json={"message": "not found"})
    )
    async with ShortcutClient(token="x") as client:
        with pytest.raises(ShortcutClientError) as info:
            await client.get("/stories/9999")
    assert info.value.status_code == 404


@pytest.mark.asyncio
@respx.mock
async def test_connection_error_retries_on_get() -> None:
    route = respx.get("https://api.app.shortcut.com/api/v3/stories/1").mock(
        side_effect=[
            httpx.ConnectError("first"),
            httpx.Response(200, json={"id": 1}),
        ]
    )
    async with ShortcutClient(token="x", max_retries=3) as client:
        result = await client.get("/stories/1")
    assert result == {"id": 1}
    assert route.call_count == 2
