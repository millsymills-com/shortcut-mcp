"""Unit tests for the cassette PII scrubber.

The scrubber runs at record time (`before_record_response`); these tests pin its
behaviour directly so a regression is caught without re-recording a cassette.
"""

from __future__ import annotations

from tests.contract.conftest import (
    REDACTED_EMAIL,
    REDACTED_GRAVATAR_HASH,
    REDACTED_MENTION_NAME,
    _scrub_pii,
)

_REAL_MD5 = "d41d8cd98f00b204e9800998ecf8427e"


def test_scrub_rewrites_gravatar_avatar_url_preserving_query() -> None:
    member = {
        "display_icon": f"https://www.gravatar.com/avatar/{_REAL_MD5}?s=40&d=identicon",
    }
    out = _scrub_pii(member)
    assert out["display_icon"] == (f"https://www.gravatar.com/avatar/{REDACTED_GRAVATAR_HASH}?s=40&d=identicon")


def test_scrub_rewrites_gravatar_md5_regardless_of_carrying_key() -> None:
    # The reversible MD5 must die in any string field, not just gravatar_hash.
    out = _scrub_pii({"icon": {"url": f"https://www.gravatar.com/avatar/{_REAL_MD5}"}})
    assert _REAL_MD5 not in out["icon"]["url"]


def test_scrub_still_redacts_known_keys_and_emails() -> None:
    out = _scrub_pii(
        {
            "mention_name": "realhandle",
            "gravatar_hash": _REAL_MD5,
            "profile": {"email_address": "person@real.example"},
        }
    )
    assert out["mention_name"] == REDACTED_MENTION_NAME
    assert out["gravatar_hash"] == REDACTED_GRAVATAR_HASH
    assert out["profile"]["email_address"] == REDACTED_EMAIL
