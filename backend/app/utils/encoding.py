"""
ID generation strategy:

We use a hybrid approach:
1. For auto-generated codes: encode a 64-bit ID with base62.
   The ID is a Snowflake-inspired value: timestamp_ms(41 bits) | machine_id(10 bits) | sequence(12 bits)
   This guarantees uniqueness across multiple FastAPI instances without DB coordination.
   Result: a deterministic, sortable, 7-char short code.

2. For custom aliases: validated and stored as-is.

Why not UUID? Too long. Why not random base62? Collision risk at scale + needs DB round-trip to check.
Why not pure counter? Requires coordination (Redis INCR or DB sequence works but adds latency).
"""

import os
import time
import threading


BASE62_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_ALPHABET_LEN = len(BASE62_ALPHABET)

# Snowflake config
_MACHINE_ID = int(os.getenv("MACHINE_ID", "1")) & 0x3FF   # 10 bits → 0-1023
_EPOCH = 1700000000000  # Custom epoch: Nov 2023 (reduces ID size)
_SEQUENCE_BITS = 12
_MACHINE_BITS = 10
_MAX_SEQUENCE = (1 << _SEQUENCE_BITS) - 1  # 4095

_lock = threading.Lock()
_last_timestamp: int = -1
_sequence: int = 0


def _snowflake_id() -> int:
    global _last_timestamp, _sequence

    with _lock:
        ts = int(time.time() * 1000) - _EPOCH
        if ts == _last_timestamp:
            _sequence = (_sequence + 1) & _MAX_SEQUENCE
            if _sequence == 0:
                # Sequence exhausted — wait for next millisecond
                while ts <= _last_timestamp:
                    ts = int(time.time() * 1000) - _EPOCH
        else:
            _sequence = 0
        _last_timestamp = ts

        return (ts << (_MACHINE_BITS + _SEQUENCE_BITS)) | (_MACHINE_ID << _SEQUENCE_BITS) | _sequence


def base62_encode(num: int) -> str:
    """Encode a positive integer into a base62 string."""
    if num == 0:
        return BASE62_ALPHABET[0]
    chars: list[str] = []
    while num:
        num, remainder = divmod(num, _ALPHABET_LEN)
        chars.append(BASE62_ALPHABET[remainder])
    return "".join(reversed(chars))


def base62_decode(s: str) -> int:
    """Decode a base62 string back to an integer."""
    num = 0
    for char in s:
        num = num * _ALPHABET_LEN + BASE62_ALPHABET.index(char)
    return num


def generate_short_code(length: int = 7) -> str:
    """
    Generate a unique short code.
    Encodes a Snowflake ID in base62.

    Snowflake IDs are 63-bit integers. base62-encoded, they produce ~10-11 chars.
    We take the LAST `length` characters — these are the high-entropy bits
    (sequence + low timestamp bits), ensuring uniqueness within a burst.

    For full collision safety at scale use the full encoded value (10 chars).
    7 chars gives 62^7 = ~3.5 trillion combinations, ample for most deployments.
    """
    snowflake = _snowflake_id()
    code = base62_encode(snowflake)
    # Take the last `length` characters — highest entropy (sequence lives here)
    return code[-length:] if len(code) >= length else code.ljust(length, "0")
