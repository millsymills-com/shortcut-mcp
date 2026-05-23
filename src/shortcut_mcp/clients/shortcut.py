"""Async httpx client for the Shortcut REST API."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl, quote, urlsplit

if TYPE_CHECKING:
    from types import TracebackType

import httpx
from httpx._multipart import MultipartStream
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from shortcut_mcp.errors import (
    ShortcutAuthError,
    ShortcutClientError,
    ShortcutConnectionError,
    ShortcutError,
    ShortcutRateLimitedError,
    ShortcutServerError,
    ShortcutTimeoutError,
)

DEFAULT_BASE_URL = "https://api.app.shortcut.com/api/v3"
IDEMPOTENT_METHODS = frozenset({"GET", "HEAD"})
RETRYABLE_EXCEPTIONS = (ShortcutTimeoutError, ShortcutConnectionError)


_API_PREFIX = "/api/v3"


def _split_next(nxt: str) -> tuple[str, dict[str, str]]:
    """Parse a Shortcut `next` cursor (path + query) into a client-relative (path, params)."""
    parts = urlsplit(nxt)
    if parts.netloc:
        raise ValueError(f"next cursor must be relative, not absolute: {nxt!r}")
    path = parts.path
    if path.startswith(_API_PREFIX):
        path = path[len(_API_PREFIX) :]
    if path.startswith("//"):
        raise ValueError(f"next cursor path must not be scheme-relative: {path!r}")
    if not path.startswith("/"):
        raise ValueError(f"next cursor path must have a leading slash: {path!r}")
    return path, dict(parse_qsl(parts.query))


def _seg(value: str) -> str:
    """Percent-encode a path segment with no reserved characters allowed."""
    return quote(value, safe="")


def _validate_path(path: str) -> None:
    if "://" in path:
        raise ValueError(f"path must be relative, not absolute: {path!r}")
    if not path.startswith("/"):
        raise ValueError(f"path must have a leading slash: {path!r}")


def _safe_body(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


def _parse_retry_after(response: httpx.Response) -> float | None:
    raw = response.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _map_status_to_error(response: httpx.Response) -> ShortcutError:
    body = _safe_body(response)
    if response.status_code == 401:
        return ShortcutAuthError(status_code=401, body=body)
    if response.status_code == 429:
        return ShortcutRateLimitedError(status_code=429, body=body, retry_after=_parse_retry_after(response))
    if 400 <= response.status_code < 500:
        return ShortcutClientError(status_code=response.status_code, body=body)
    if response.status_code >= 500:
        return ShortcutServerError(status_code=response.status_code, body=body)
    return ShortcutError(status_code=response.status_code, body=body)


class ShortcutClient:
    def __init__(
        self,
        *,
        token: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._max_retries = max_retries
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

    async def paginate(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        max_pages: int = 5,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Follow the `{data, next, total}` cursor up to max_pages / limit.

        Used by /search/* and /epics/paginated. The `next` cursor is parsed into
        a relative (path, params) so the query never lands in the path.
        """
        items: list[Any] = []
        total: int | None = None
        pages = 0
        next_path, next_params = path, dict(params or {})
        while True:
            page = await self.get(next_path, params=next_params)
            if not isinstance(page, dict):
                raise ShortcutError(
                    status_code=0,
                    body=f"paginate({path!r}): expected a paginated object, got {type(page).__name__}",
                )
            items.extend(page.get("data", []))
            page_total = page.get("total")
            if page_total is not None:
                total = page_total
            pages += 1
            nxt = page.get("next")
            if not nxt or pages >= max_pages or (limit is not None and len(items) >= limit):
                break
            next_path, next_params = _split_next(nxt)
        if limit is not None:
            items = items[:limit]
        return {"data": items, "total": total, "pages": pages}

    async def post(self, path: str, *, json: dict[str, Any]) -> Any:
        return await self._request("POST", path, json=json)

    async def put(self, path: str, *, json: dict[str, Any]) -> Any:
        return await self._request("PUT", path, json=json)

    async def delete(self, path: str, *, json: dict[str, Any] | None = None) -> Any:
        return await self._request("DELETE", path, json=json)

    async def upload(self, path: str, *, file_path: str, max_bytes: int = 50 * 1024 * 1024) -> Any:
        """Upload a local file as multipart/form-data (Shortcut POST /files)."""
        p = Path(file_path)
        if not p.is_file():
            raise ShortcutError(status_code=0, body=f"upload: not a file: {file_path!r}")
        size = p.stat().st_size
        if size > max_bytes:
            raise ShortcutError(
                status_code=0,
                body=f"upload: file too large ({size} > {max_bytes} bytes)",
            )
        _validate_path(path)
        files = {"file0": (p.name, p.read_bytes(), "application/octet-stream")}
        req = self._client.build_request("POST", path, files=files)
        # The client-level Content-Type: application/json default overrides the
        # multipart boundary httpx sets on the stream; restore it from the stream
        # (whose content_type carries the exact boundary used to encode the body).
        if not isinstance(req.stream, MultipartStream):
            raise ShortcutError(status_code=0, body="upload: failed to build a multipart request")
        req.headers["content-type"] = req.stream.content_type
        try:
            resp = await self._client.send(req)
        except httpx.TimeoutException as exc:
            raise ShortcutTimeoutError(status_code=0, body=str(exc)) from exc
        except httpx.ConnectError as exc:
            raise ShortcutConnectionError(status_code=0, body=str(exc)) from exc
        except httpx.HTTPError as exc:
            raise ShortcutConnectionError(status_code=0, body=str(exc)) from exc
        if resp.status_code >= 400:
            raise _map_status_to_error(resp)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        _validate_path(path)

        if method in IDEMPOTENT_METHODS:
            retryer = AsyncRetrying(
                retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
                stop=stop_after_attempt(self._max_retries),
                wait=wait_exponential(multiplier=0.2, max=2.0),
                reraise=True,
            )
            async for attempt in retryer:
                with attempt:
                    return await self._issue(method, path, params=params, json=json)
            return None  # unreachable; satisfies type checker
        return await self._issue(method, path, params=params, json=json)

    async def validate_connection(self) -> None:
        """Probe the API with a cheap GET to surface auth/connection issues at startup.

        Calls GET /member (the authenticated user's profile — minimal payload).
        Any ShortcutError propagates so the lifespan can classify it.
        """
        await self.get("/member")

    async def _issue(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None,
        json: dict[str, Any] | None,
    ) -> Any:
        try:
            response = await self._client.request(method, path, params=params, json=json)
        except httpx.TimeoutException as exc:
            raise ShortcutTimeoutError(status_code=0, body=str(exc)) from exc
        except httpx.ConnectError as exc:
            raise ShortcutConnectionError(status_code=0, body=str(exc)) from exc
        except httpx.HTTPError as exc:
            raise ShortcutConnectionError(status_code=0, body=str(exc)) from exc

        if response.status_code >= 400:
            raise _map_status_to_error(response)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()
