"""
Tests for core URL shortening logic.
Run: pytest tests/ -v --asyncio-mode=auto
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.utils.encoding import base62_encode, base62_decode, generate_short_code


# ── Encoding tests ─────────────────────────────────────────────────────────────

def test_base62_encode_decode_roundtrip():
    for n in [0, 1, 61, 62, 12345, 9999999999]:
        encoded = base62_encode(n)
        assert base62_decode(encoded) == n


def test_generate_short_code_length():
    code = generate_short_code(7)
    assert len(code) == 7


def test_generate_short_code_uniqueness():
    """Generate many codes and verify no duplicates."""
    codes = {generate_short_code(7) for _ in range(1000)}
    assert len(codes) == 1000, "Collision detected"


def test_short_code_charset():
    """Codes should only use base62 characters."""
    import string
    valid_chars = set(string.digits + string.ascii_letters)
    for _ in range(100):
        code = generate_short_code(7)
        assert all(c in valid_chars for c in code), f"Invalid char in {code}"


# ── URL validation tests ───────────────────────────────────────────────────────

def test_shorten_request_rejects_private_ips():
    from pydantic import ValidationError
    from app.schemas.url import ShortenRequest

    with pytest.raises(ValidationError):
        ShortenRequest(url="http://localhost/test")

    with pytest.raises(ValidationError):
        ShortenRequest(url="http://192.168.1.1/admin")


def test_shorten_request_accepts_valid_url():
    from app.schemas.url import ShortenRequest
    req = ShortenRequest(url="https://example.com/some/path?q=1")
    assert "example.com" in str(req.url)


def test_custom_alias_validation():
    from pydantic import ValidationError
    from app.schemas.url import ShortenRequest

    # Valid alias
    req = ShortenRequest(url="https://example.com", custom_alias="my-alias")
    assert req.custom_alias == "my-alias"

    # Invalid characters
    with pytest.raises(ValidationError):
        ShortenRequest(url="https://example.com", custom_alias="my alias!")


# ── Rate limiter parse test ────────────────────────────────────────────────────

def test_parse_rate():
    from app.middleware.rate_limit import _parse_rate
    assert _parse_rate("10/minute") == (10, 60)
    assert _parse_rate("100/hour") == (100, 3600)
    assert _parse_rate("5/second") == (5, 1)
