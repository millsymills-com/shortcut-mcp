"""Guard: committed cassettes must carry no unredacted PII.

Cassettes are recorded against a live workspace and committed to the repo, so a
recording regression that bypasses the scrubber must fail loudly here rather
than leak a real email address.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from tests.contract.conftest import REDACTED_EMAIL

_CASSETTE_DIR = pathlib.Path(__file__).parent / "cassettes"
_EMAIL_RE = re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


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
