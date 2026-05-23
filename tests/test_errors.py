"""Unit tests for the error taxonomy and startup classifier."""

from __future__ import annotations

import pytest

from shortcut_mcp.errors import (
    BODY_TRUNCATE_BYTES,
    ConfigError,
    ShortcutAuthError,
    ShortcutClientError,
    ShortcutConnectionError,
    ShortcutError,
    ShortcutRateLimitedError,
    ShortcutServerError,
    ShortcutTimeoutError,
    _classify_startup_error,
)


def test_base_carries_status_and_body() -> None:
    err = ShortcutError(status_code=404, body={"message": "not found"})
    assert err.status_code == 404
    assert err.body == {"message": "not found"}


def test_body_truncated_when_string_too_large() -> None:
    huge = "x" * (BODY_TRUNCATE_BYTES + 1000)
    err = ShortcutError(status_code=500, body=huge)
    assert isinstance(err.body, str)
    assert len(err.body) == BODY_TRUNCATE_BYTES


def test_body_not_truncated_when_dict() -> None:
    body = {"message": "auth", "code": 401}
    err = ShortcutError(status_code=401, body=body)
    assert err.body == body


def test_subclasses_inherit_base() -> None:
    for cls in (
        ShortcutAuthError,
        ShortcutClientError,
        ShortcutRateLimitedError,
        ShortcutServerError,
        ShortcutTimeoutError,
        ShortcutConnectionError,
    ):
        assert issubclass(cls, ShortcutError)


def test_rate_limited_records_retry_after() -> None:
    err = ShortcutRateLimitedError(status_code=429, body=None, retry_after=12.5)
    assert err.retry_after == 12.5


@pytest.mark.parametrize(
    ("exc", "needle"),
    [
        (ShortcutAuthError(status_code=401, body=None), "SHORTCUT_API_TOKEN"),
        (ShortcutTimeoutError(status_code=0, body=None), "did not respond"),
        (ShortcutConnectionError(status_code=0, body=None), "cannot reach"),
        (ShortcutServerError(status_code=503, body=None), "unhealthy"),
        (ConfigError("bad"), "config"),
    ],
)
def test_classify_startup_error_actionable(exc: Exception, needle: str) -> None:
    hint = _classify_startup_error(exc)
    assert needle.lower() in hint.lower()
