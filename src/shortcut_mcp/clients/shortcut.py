"""Async httpx client for the Shortcut REST API.

Retry + error-mapping layer is implemented in Task 11; this module
provides the core: URL validation, path encoding, and generic verbs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import httpx

if TYPE_CHECKING:
    from types import TracebackType

DEFAULT_BASE_URL = "https://api.app.shortcut.com/api/v3"


def _seg(value: str) -> str:
    """Percent-encode a path segment.

    Use for any caller-controlled fragment that becomes part of the URL
    path (story IDs from URLs, label names with slashes, etc.). The empty
    `safe=""` arg means *every* reserved character is escaped, so a
    segment cannot accidentally traverse path boundaries.
    """
    return quote(value, safe="")


def _validate_path(path: str) -> None:
    """Reject paths that could redirect the auth header to a different host."""
    if "://" in path:
        raise ValueError(f"path must be relative, not absolute: {path!r}")
    if not path.startswith("/"):
        raise ValueError(f"path must have a leading slash: {path!r}")


class ShortcutClient:
    def __init__(
        self,
        *,
        token: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Shortcut-Token": token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=timeout,
        )

    async def __aenter__(self) -> ShortcutClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, *, json: dict[str, Any]) -> Any:
        return await self._request("POST", path, json=json)

    async def put(self, path: str, *, json: dict[str, Any]) -> Any:
        return await self._request("PUT", path, json=json)

    async def delete(self, path: str) -> Any:
        return await self._request("DELETE", path)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        _validate_path(path)
        response = await self._client.request(method, path, params=params, json=json)
        # Error-mapping + retry come in Task 11. Core: raise raw on error,
        # return None for 204, JSON otherwise.
        if response.status_code == 204 or not response.content:
            return None
        response.raise_for_status()
        return response.json()
