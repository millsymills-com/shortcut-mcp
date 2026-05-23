"""Typed exception taxonomy for the Shortcut MCP server."""

from __future__ import annotations

from typing import Any

BODY_TRUNCATE_BYTES = 4096


def _truncate(body: Any) -> Any:
    if isinstance(body, str) and len(body) > BODY_TRUNCATE_BYTES:
        return body[:BODY_TRUNCATE_BYTES]
    return body


class ShortcutError(Exception):
    """Base for any Shortcut API or transport failure."""

    def __init__(self, *, status_code: int, body: Any) -> None:
        super().__init__(f"Shortcut error {status_code}: {body!r}")
        self.status_code = status_code
        self.body = _truncate(body)


class ShortcutAuthError(ShortcutError):
    """401 — token invalid or revoked."""


class ShortcutClientError(ShortcutError):
    """Any 4xx that isn't 401 or 429 (400, 403, 404, 409, ...)."""


class ShortcutRateLimitedError(ShortcutError):
    """429 — never retried; surfaced to caller."""

    def __init__(self, *, status_code: int, body: Any, retry_after: float | None = None) -> None:
        super().__init__(status_code=status_code, body=body)
        self.retry_after = retry_after


class ShortcutServerError(ShortcutError):
    """5xx — not auto-retried in v0.1."""


class ShortcutTimeoutError(ShortcutError):
    """Wraps httpx.TimeoutException. Retried on GET/HEAD only."""


class ShortcutConnectionError(ShortcutError):
    """Wraps httpx.ConnectError / network failures. Retried on GET/HEAD only."""


class ConfigError(Exception):
    """Misconfiguration caught at startup."""


def _classify_startup_error(exc: BaseException) -> str:
    """Convert a startup exception into a short, actionable operator hint."""
    if isinstance(exc, ShortcutAuthError):
        return "authentication rejected by Shortcut — regenerate SHORTCUT_API_TOKEN"
    if isinstance(exc, ShortcutTimeoutError):
        return "Shortcut API did not respond in time — check network / SHORTCUT_REQUEST_TIMEOUT"
    if isinstance(exc, ShortcutConnectionError):
        return "cannot reach api.app.shortcut.com — check network / DNS / SHORTCUT_API_BASE_URL"
    if isinstance(exc, ShortcutServerError):
        return "Shortcut API returned 5xx — upstream may be unhealthy, retry later"
    if isinstance(exc, ShortcutError):
        return f"Shortcut API error: {type(exc).__name__}"
    if isinstance(exc, ConfigError):
        return f"invalid config: {exc}"
    return f"unexpected error ({type(exc).__name__})"
