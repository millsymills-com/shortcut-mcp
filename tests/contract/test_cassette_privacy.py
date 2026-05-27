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
# The gravatar hash is reversible (rainbow tables) and the same value rides
# inside avatar URLs (e.g. display_icon), bypassing the key-based field guards.
# This guard is deliberately broader than the `conftest` scrubber (which rewrites
# only `gravatar.com/avatar/<hash>`) so a scrubber regression fails loudly here
# rather than leaking silently. The secret is the trailing hex run, so the guard
# keys on host + hash and tolerates any intervening path shape:
#   - `/avatar/`, `/userimage/<id>/<hash>`, `/blavatar/`, multi-segment ids
#     (`/userimage/<uid>/<iid>/<hash>`), and any future image endpoint
#   - `re.IGNORECASE` case-folds the whole pattern (host and path segments)
#   - `%2F`-encoded separators are matched alongside literal `/`
#   - host shard / `secure.` variants (e.g. `0.gravatar.com`) match because the
#     pattern is unanchored — any subdomain prefix before `gravatar.com` is ignored
# `{32,}` captures the full hex run so a partially-scrubbed SHA-256 (sentinel
# prefix + real trailing half) is still flagged rather than masked by the prefix.
#
# Accepted residual gaps (documented, not guarded — no live leak today):
#   - JSON-escaped slash `gravatar.com\/avatar\/`: benign in our pipeline
#     (`json.dumps` does not escape `/`); only a hand-edited/external cassette
#     could carry it.
#   - A bare MD5/SHA-256 in free text outside a gravatar URL: not redacted, to
#     avoid clobbering legitimate 32-hex IDs that share the hash's shape.
_GRAVATAR_URL_RE = re.compile(
    rb"gravatar\.com"  # host (unanchored: any subdomain shard may precede it)
    rb"(?:(?:/|%2[fF])[0-9a-z._-]+)*"  # arbitrary path segments (avatar/userimage/blavatar, numeric ids)
    rb"(?:/|%2[fF])"  # separator before the hash
    rb"([0-9a-fA-F]{32,})",  # reversible MD5/SHA-256 hex run
    re.IGNORECASE,
)


def _unredacted_gravatar_hashes(raw: bytes) -> set[str]:
    return {h.decode() for h in _GRAVATAR_URL_RE.findall(raw) if h.decode() != REDACTED_GRAVATAR_HASH}


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


def test_unredacted_gravatar_hashes_flags_real_md5() -> None:
    raw = b'{"display_icon": "https://www.gravatar.com/avatar/d41d8cd98f00b204e9800998ecf8427e?s=40"}'
    assert _unredacted_gravatar_hashes(raw) == {"d41d8cd98f00b204e9800998ecf8427e"}


def test_unredacted_gravatar_hashes_ignores_sentinel() -> None:
    raw = f'{{"display_icon": "https://www.gravatar.com/avatar/{REDACTED_GRAVATAR_HASH}"}}'.encode()
    assert _unredacted_gravatar_hashes(raw) == set()


def test_unredacted_gravatar_hashes_flags_partial_sha256_leak() -> None:
    # A fixed-32 scrubber would leave sentinel + real trailing half; capturing the
    # full hex run keeps the sentinel prefix from masking the leaked remnant.
    tail = "00112233445566778899aabbccddeeff"
    raw = f'{{"display_icon": "https://www.gravatar.com/avatar/{REDACTED_GRAVATAR_HASH}{tail}"}}'.encode()
    assert _unredacted_gravatar_hashes(raw) == {f"{REDACTED_GRAVATAR_HASH}{tail}"}


def test_unredacted_gravatar_hashes_flags_userimage_path() -> None:
    # `/userimage/<id>/<hash>` is unscrubbed today; the guard must over-match it.
    md5 = "d41d8cd98f00b204e9800998ecf8427e"
    raw = f'{{"display_icon": "https://0.gravatar.com/userimage/12345678/{md5}?size=80"}}'.encode()
    assert _unredacted_gravatar_hashes(raw) == {md5}


def test_unredacted_gravatar_hashes_flags_secure_shard_host() -> None:
    md5 = "d41d8cd98f00b204e9800998ecf8427e"
    raw = f'{{"display_icon": "https://secure.gravatar.com/avatar/{md5}"}}'.encode()
    assert _unredacted_gravatar_hashes(raw) == {md5}


def test_unredacted_gravatar_hashes_flags_uppercase_host() -> None:
    md5 = "d41d8cd98f00b204e9800998ecf8427e"
    raw = f'{{"display_icon": "https://GRAVATAR.COM/AVATAR/{md5}"}}'.encode()
    assert _unredacted_gravatar_hashes(raw) == {md5}


def test_unredacted_gravatar_hashes_flags_percent_encoded_slashes() -> None:
    md5 = "d41d8cd98f00b204e9800998ecf8427e"
    raw = f'{{"display_icon": "https://gravatar.com%2Favatar%2F{md5}"}}'.encode()
    assert _unredacted_gravatar_hashes(raw) == {md5}


def test_unredacted_gravatar_hashes_flags_userimage_multi_segment_id() -> None:
    # Legacy custom uploads carry two numeric segments before the hash; the
    # path-agnostic guard must match regardless of segment count.
    md5 = "d41d8cd98f00b204e9800998ecf8427e"
    raw = f'{{"display_icon": "https://gravatar.com/userimage/12/34/{md5}"}}'.encode()
    assert _unredacted_gravatar_hashes(raw) == {md5}


def test_unredacted_gravatar_hashes_flags_blavatar_path() -> None:
    # `/blavatar/` is neither avatar nor userimage but carries the same hash.
    md5 = "d41d8cd98f00b204e9800998ecf8427e"
    raw = f'{{"display_icon": "https://gravatar.com/blavatar/{md5}"}}'.encode()
    assert _unredacted_gravatar_hashes(raw) == {md5}


def test_unredacted_gravatar_hashes_flags_sha256_in_userimage_path() -> None:
    # Gravatar now emits 64-hex SHA-256; the riskiest leak is a full run on a
    # non-avatar path the scrubber never touches.
    sha256 = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    raw = f'{{"display_icon": "https://gravatar.com/userimage/9/{sha256}"}}'.encode()
    assert _unredacted_gravatar_hashes(raw) == {sha256}


def test_unredacted_gravatar_hashes_flags_lowercase_percent_encoded_slash() -> None:
    # Real URLs vary the percent-encoding case; lowercase `%2f` must match too.
    md5 = "d41d8cd98f00b204e9800998ecf8427e"
    raw = f'{{"display_icon": "https://gravatar.com%2favatar%2f{md5}"}}'.encode()
    assert _unredacted_gravatar_hashes(raw) == {md5}


def test_unredacted_gravatar_hashes_flags_multiple_distinct_hashes() -> None:
    # A cassette holds many members; the set must accumulate every leaked hash.
    first = "d41d8cd98f00b204e9800998ecf8427e"
    second = "5d41402abc4b2a76b9719d911017c592"
    raw = (f'{{"a": "https://gravatar.com/avatar/{first}", "b": "https://gravatar.com/avatar/{second}"}}').encode()
    assert _unredacted_gravatar_hashes(raw) == {first, second}


def test_unredacted_gravatar_hashes_ignores_sub_32_hex_run() -> None:
    # A 31-hex run is below the hash floor; flagging it would create false
    # positives on legitimate short hex IDs.
    raw = b'{"display_icon": "https://gravatar.com/avatar/d41d8cd98f00b204e9800998ecf8427"}'
    assert _unredacted_gravatar_hashes(raw) == set()


def test_unredacted_gravatar_hashes_ignores_json_escaped_slash() -> None:
    # Documented residual: an escaped `\/` separator is not guarded (benign in
    # our pipeline — `json.dumps` emits a literal `/`).
    md5 = "d41d8cd98f00b204e9800998ecf8427e"
    raw = rb'{"display_icon": "https://gravatar.com\/avatar\/' + md5.encode() + rb'"}'
    assert _unredacted_gravatar_hashes(raw) == set()


@pytest.mark.contract
def test_cassettes_contain_no_unredacted_gravatar_url() -> None:
    cassettes = list(_CASSETTE_DIR.rglob("*.yaml"))
    if not cassettes:
        pytest.skip("no cassettes recorded yet")
    leaked: set[str] = set()
    for cassette in cassettes:
        leaked |= _unredacted_gravatar_hashes(cassette.read_bytes())
    assert not leaked, f"unredacted gravatar MD5(s) in avatar URLs: {sorted(leaked)}"
