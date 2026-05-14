"""Webhook signature key-id versioning (S4-J3).

Outgoing webhooks have always been HMAC-signed with a single secret.
Sprint 4 lets the operator hold N versions of the secret simultaneously
and rotate by adding a new one + revoking the old. Signatures emit a
header of the form `dclaw-signature: t=<ts>, k=<key_id>, v1=<sig>` so
receivers can pick the right key.

Keys live in `settings.webhook_signing_keys_json`:

    [
      {"key_id": "k_2026_05", "secret": "...", "active": true,  "primary": true},
      {"key_id": "k_2026_01", "secret": "...", "active": false, "primary": false}
    ]

`current_primary()` returns the key used for signing; `lookup(key_id)`
returns the secret for verification.
"""

from __future__ import annotations

import hmac
import json
import logging
from dataclasses import dataclass
from hashlib import sha256
from time import time
from typing import Iterable

from app.core.config import settings

log = logging.getLogger(__name__)


@dataclass
class SigningKey:
    key_id: str
    secret: str
    active: bool = True
    primary: bool = False


def _load_keys() -> list[SigningKey]:
    raw = getattr(settings, "webhook_signing_keys_json", None) or "[]"
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except Exception:  # noqa: BLE001
            return []
    else:
        data = raw
    out: list[SigningKey] = []
    for d in data:
        out.append(
            SigningKey(
                key_id=d["key_id"],
                secret=d["secret"],
                active=bool(d.get("active", True)),
                primary=bool(d.get("primary", False)),
            )
        )
    return out


def current_primary() -> SigningKey | None:
    keys = _load_keys()
    primary = next((k for k in keys if k.primary and k.active), None)
    if primary is None and keys:
        primary = next((k for k in keys if k.active), None)
    return primary


def lookup(key_id: str) -> SigningKey | None:
    for k in _load_keys():
        if k.key_id == key_id and k.active:
            return k
    return None


def sign_body(body: bytes) -> str:
    """Return a `t=,k=,v1=` signature header value for an outgoing
    webhook body. Falls back to a single-key signature derived from
    settings.webhook_signing_secret when no key list is configured —
    keeps legacy receivers working through the rotation."""
    primary = current_primary()
    ts = str(int(time()))
    if primary:
        msg = f"{ts}.".encode("utf-8") + body
        sig = hmac.new(primary.secret.encode(), msg, sha256).hexdigest()
        return f"t={ts}, k={primary.key_id}, v1={sig}"
    # Legacy single-secret path.
    legacy = getattr(settings, "webhook_signing_secret", None) or ""
    msg = f"{ts}.".encode("utf-8") + body
    sig = hmac.new(legacy.encode(), msg, sha256).hexdigest() if legacy else ""
    return f"t={ts}, v1={sig}"


def verify_header(header_value: str, body: bytes, max_skew_seconds: int = 300) -> bool:
    """Verify a `t=,k=,v1=` signature header against the request body."""
    parts = dict(
        (p.strip().split("=", 1)[0], p.strip().split("=", 1)[1])
        for p in header_value.split(",")
        if "=" in p
    )
    ts = parts.get("t", "")
    key_id = parts.get("k", "")
    sig = parts.get("v1", "")
    if not ts.isdigit():
        return False
    if abs(int(ts) - int(time())) > max_skew_seconds:
        return False
    secret: str | None = None
    if key_id:
        k = lookup(key_id)
        secret = k.secret if k else None
    if secret is None:
        legacy = getattr(settings, "webhook_signing_secret", None) or None
        secret = legacy
    if not secret:
        return False
    expected = hmac.new(
        secret.encode(), f"{ts}.".encode("utf-8") + body, sha256
    ).hexdigest()
    return hmac.compare_digest(expected, sig)
