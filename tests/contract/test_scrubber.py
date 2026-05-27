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
_REAL_SHA256 = "a1b2c3d4e5f6071829304a5b6c7d8e9f00112233445566778899aabbccddeeff"


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


def test_scrub_consumes_full_sha256_hash_no_trailing_remnant() -> None:
    # A fixed-32 match would leave the hash's second half in the URL; the whole
    # hex run must be redacted so no reversible fragment survives.
    out = _scrub_pii({"display_icon": f"https://www.gravatar.com/avatar/{_REAL_SHA256}?s=40"})
    assert _REAL_SHA256 not in out["display_icon"]
    assert _REAL_SHA256[32:] not in out["display_icon"]
    assert out["display_icon"] == f"https://www.gravatar.com/avatar/{REDACTED_GRAVATAR_HASH}?s=40"


def test_scrub_rewrites_userimage_path_preserving_id() -> None:
    # Non-avatar paths the scrubber must also redact; the numeric id (not the
    # email-derived hash) is preserved so the URL shape survives.
    out = _scrub_pii({"display_icon": f"https://0.gravatar.com/userimage/12345678/{_REAL_MD5}?size=80"})
    assert _REAL_MD5 not in out["display_icon"]
    assert out["display_icon"] == f"https://0.gravatar.com/userimage/12345678/{REDACTED_GRAVATAR_HASH}?size=80"


def test_scrub_rewrites_multi_segment_and_blavatar_paths() -> None:
    out = _scrub_pii(
        {
            "a": f"https://gravatar.com/userimage/12/34/{_REAL_MD5}",
            "b": f"https://gravatar.com/blavatar/{_REAL_MD5}",
        }
    )
    assert _REAL_MD5 not in out["a"]
    assert _REAL_MD5 not in out["b"]
    assert out["a"] == f"https://gravatar.com/userimage/12/34/{REDACTED_GRAVATAR_HASH}"
    assert out["b"] == f"https://gravatar.com/blavatar/{REDACTED_GRAVATAR_HASH}"


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
