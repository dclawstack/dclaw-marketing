"""Fernet-backed secret box for tenant-scoped credentials.

Per IMPLEMENTATION-PLAN §Phase 6 / Appendix A.6:
- The master KMS key lives in `settings.tenant_encryption_master_key`
  (base64-encoded Fernet key). Set via env in prod; checked-in default
  is dev-only.
- Per-Org key derivation is a v2.1+ concern — for v0 we encrypt
  every secret with the master key directly. The blob format stays
  forward-compatible (Fernet token); a future migration can re-wrap
  blobs under per-Org keys without changing the column.

Usage:
    from app.services.secret_box import seal, unseal
    sealed = seal("my-oauth-access-token")   # bytes
    plain  = unseal(sealed)                   # str
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    key = settings.tenant_encryption_master_key
    if not key:
        raise RuntimeError(
            "tenant_encryption_master_key is unset; cannot seal secrets."
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def seal(plaintext: str) -> bytes:
    """Encrypt a UTF-8 string. Returns the raw Fernet token (bytes)."""
    if plaintext is None:
        raise ValueError("Cannot seal None.")
    return _fernet().encrypt(plaintext.encode("utf-8"))


def unseal(token: bytes | str) -> str:
    """Decrypt a Fernet token. Raises InvalidToken on tamper or wrong key."""
    if token is None:
        raise ValueError("Cannot unseal None.")
    t = token.encode() if isinstance(token, str) else token
    return _fernet().decrypt(t).decode("utf-8")


def try_unseal(token: bytes | str) -> str | None:
    """Best-effort unseal — returns None on InvalidToken instead of raising.

    Useful in list endpoints where we want to show "tampered/expired"
    without crashing the whole response.
    """
    try:
        return unseal(token)
    except InvalidToken:
        return None
