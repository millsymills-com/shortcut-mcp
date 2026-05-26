"""Guard: committed cassettes must carry no unredacted PII.

Cassettes are recorded against a live workspace and committed to the repo, so a
recording regression that bypasses the scrubber must fail loudly here rather
than leak a real email address.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from tests.contract.conftest import (
    REDACTED_EMAIL,
    REDACTED_GRAVATAR_HASH,
    REDACTED_MENTION_NAME,
)

_CASSETTE_DIR = pathlib.Path(__file__).parent / "cassettes"
_EMAIL_RE = re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Captures the value of each member-identity field so the guard can assert it
# equals the redaction sentinel rather than a real handle / gravatar MD5.
_PII_FIELD_RES = {
    "mention_name": (re.compile(rb'"mention_name":\s*"([^"]*)"'), REDACTED_MENTION_NAME),
    "gravatar_hash": (re.compile(rb'"gravatar_hash":\s*"([^"]*)"'), REDACTED_GRAVATAR_HASH),
}


@pytest.mark.contract
def test_cassettes_contain_no_unredacted_email() -> None:
    cassettes = list(_CASSETTE_DIR.rglob("*.yaml"))
    if not cassettes:
        pytest.skip("no cassettes recorded yet")
    leaked: set[str] = set()
    for cassette in cassettes:
        for match in _EMAIL_RE.findall(cassette.read_bytes()):
            leaked.add(match.decode())
    leaked.discard(REDACTED_EMAIL)
    assert not leaked, f"unredacted email(s) in cassettes: {sorted(leaked)}"


@pytest.mark.contract
def test_cassettes_contain_no_unredacted_member_identity() -> None:
    cassettes = list(_CASSETTE_DIR.rglob("*.yaml"))
    if not cassettes:
        pytest.skip("no cassettes recorded yet")
    leaked: dict[str, set[str]] = {}
    for cassette in cassettes:
        raw = cassette.read_bytes()
        for field, (pattern, sentinel) in _PII_FIELD_RES.items():
            for match in pattern.findall(raw):
                value = match.decode()
                if value != sentinel:
                    leaked.setdefault(field, set()).add(value)
    assert not leaked, f"unredacted member-identity value(s) in cassettes: {leaked}"
