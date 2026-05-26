"""VCR config for contract tests.

Cassettes replay recorded Shortcut responses so these tests run offline in CI
(record mode defaults to ``none``). Re-record locally against the live
workspace:

    SHORTCUT_API_TOKEN=<token> uv run pytest tests/contract --record-mode=once

Two scrubbers keep cassettes safe to commit to a public repo: the
``Shortcut-Token`` auth header is filtered out, and member ``email_address``
values are redacted from response bodies before write.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest

REDACTED_EMAIL = "redacted@example.com"

# Match an email in any string value, not just the `email_address` key — emails
# also surface in descriptions, comment text and mention fields.
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _scrub_emails(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _scrub_emails(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_scrub_emails(item) for item in value]
    if isinstance(value, str):
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
    scrubbed = json.dumps(_scrub_emails(parsed))
    response["body"]["string"] = scrubbed.encode("utf-8") if isinstance(raw, bytes | bytearray) else scrubbed
    return response


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, Any]:
    return {
        "filter_headers": [("Shortcut-Token", "DUMMY")],
        "before_record_response": _before_record_response,
        "decode_compressed_response": True,
    }
