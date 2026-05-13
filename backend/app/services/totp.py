"""Stdlib TOTP helper (A.11.6).

RFC 6238 TOTP with HMAC-SHA1, 30s period, 6-digit codes. Implemented
without third-party dependencies so we don't add pyotp + qrcode to the
runtime image.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct
import time
from urllib.parse import quote


DEFAULT_PERIOD = 30
DEFAULT_DIGITS = 6


def random_secret(length_bytes: int = 20) -> str:
    """Return a fresh base32-encoded secret suitable for an authenticator."""
    raw = os.urandom(length_bytes)
    # No padding — most authenticator apps accept both, but the bare form
    # is canonical.
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _now_step(period: int = DEFAULT_PERIOD) -> int:
    return int(time.time()) // period


def generate_code(
    secret_b32: str, t_step: int | None = None, digits: int = DEFAULT_DIGITS
) -> str:
    if t_step is None:
        t_step = _now_step()
    # Pad back to a length divisible by 8 chars (5 bytes).
    pad = "=" * (-len(secret_b32) % 8)
    key = base64.b32decode(secret_b32 + pad, casefold=True)
    msg = struct.pack(">Q", t_step)
    mac = hmac.new(key, msg, hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    val = (
        ((mac[offset] & 0x7F) << 24)
        | ((mac[offset + 1] & 0xFF) << 16)
        | ((mac[offset + 2] & 0xFF) << 8)
        | (mac[offset + 3] & 0xFF)
    )
    code = val % (10**digits)
    return str(code).zfill(digits)


def verify_code(
    secret_b32: str,
    submitted: str,
    *,
    window: int = 1,
    period: int = DEFAULT_PERIOD,
    digits: int = DEFAULT_DIGITS,
) -> bool:
    """Constant-time check of `submitted` against current ± `window` steps."""
    submitted = "".join(ch for ch in submitted if ch.isdigit())
    if len(submitted) != digits:
        return False
    now_step = _now_step(period)
    for delta in range(-window, window + 1):
        expected = generate_code(secret_b32, now_step + delta, digits)
        if hmac.compare_digest(expected, submitted):
            return True
    return False


def otpauth_url(
    secret_b32: str,
    *,
    label: str,
    issuer: str = "DClaw Marketing",
    digits: int = DEFAULT_DIGITS,
    period: int = DEFAULT_PERIOD,
) -> str:
    """Build the otpauth:// URL that authenticator apps consume."""
    label_q = quote(f"{issuer}:{label}", safe=":@")
    issuer_q = quote(issuer, safe="")
    return (
        f"otpauth://totp/{label_q}?secret={secret_b32}"
        f"&issuer={issuer_q}&digits={digits}&period={period}&algorithm=SHA1"
    )
