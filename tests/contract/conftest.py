"""VCR config for contract tests.

Cassettes replay recorded Shortcut responses so these tests run offline in CI
(record mode defaults to ``none``). Re-record locally against the live
workspace:

    SHORTCUT_API_TOKEN=<token> uv run pytest tests/contract --record-mode=once

Scrubbers keep cassettes safe to commit to a public repo: the ``Shortcut-Token``
auth header is filtered out, email addresses are redacted from response bodies,
and member-identity fields are replaced by key — ``gravatar_hash`` is an MD5 of
the real email (reversible via rainbow tables) and ``mention_name`` is a handle.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest

REDACTED_EMAIL = "redacted@example.com"
REDACTED_MENTION_NAME = "redacted"
REDACTED_GRAVATAR_HASH = "0" * 32

# Member-identity fields scrubbed by key, avoiding a broad `name` redaction that
# would clobber workspace/label/epic names. `mention_name` also appears on groups;
# scrubbing it there is a harmless fixture-only side effect.
_PII_KEYS = {
    "mention_name": REDACTED_MENTION_NAME,
    "gravatar_hash": REDACTED_GRAVATAR_HASH,
}

# Match an email in any string value, not just the `email_address` key — emails
# also surface in descriptions, comment text and mention fields.
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# The same reversible hash redacted from `gravatar_hash` also rides inside avatar
# URLs (e.g. `display_icon`), so rewrite it wherever it appears in a string. The
# run is `{32,}` not `{32}`: Gravatar now emits SHA-256 (64 hex) as well as MD5,
# and a fixed-32 match would leave the hash's trailing half in the cassette.
_GRAVATAR_URL_RE = re.compile(r"(gravatar\.com/avatar/)[0-9a-fA-F]{32,}")


def _scrub_pii(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _PII_KEYS[key] if key in _PII_KEYS and isinstance(val, str) else _scrub_pii(val)
            for key, val in value.items()
        }
    if isinstance(value, list):
        return [_scrub_pii(item) for item in value]
    if isinstance(value, str):
        value = _GRAVATAR_URL_RE.sub(rf"\g<1>{REDACTED_GRAVATAR_HASH}", value)
        return _EMAIL_RE.sub(REDACTED_EMAIL, value)
    return value


def _before_record_response(response: dict[str, Any]) -> dict[str, Any]:
    raw = response.get("body", {}).get("string")
    if raw is None:
        return response
    text = raw.decode("utf-8") if isinstance(raw, bytes | bytearray) else raw
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return response
    scrubbed = json.dumps(_scrub_pii(parsed))
    response["body"]["string"] = scrubbed.encode("utf-8") if isinstance(raw, bytes | bytearray) else scrubbed
    return response


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, Any]:
    return {
        "filter_headers": [("Shortcut-Token", "DUMMY")],
        "before_record_response": _before_record_response,
        "decode_compressed_response": True,
    }
