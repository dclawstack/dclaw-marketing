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

import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


logger = logging.getLogger(__name__)


# Default placeholder in config.py. If we see this at boot we know the
# operator never set their own key, so we surface a clearer error
# message at the call site than Fernet's raw "must be 32 url-safe
# base64-encoded bytes."
_PLACEHOLDER_KEY = "change-me-fernet-master-key-base64=="


class SecretBoxNotConfiguredError(RuntimeError):
    """Raised when seal()/unseal() can't operate because the master key
    is missing or invalid. Callers should translate this into a clean
    HTTP 500 with a configuration-hint message rather than letting the
    raw cryptography exception bubble. (S5 #360)
    """


def _fernet() -> Fernet:
    key = settings.tenant_encryption_master_key
    if not key:
        raise SecretBoxNotConfiguredError(
            "TENANT_ENCRYPTION_MASTER_KEY is unset. Generate one with "
            "`python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\"` and set it in the "
            "environment."
        )
    if key == _PLACEHOLDER_KEY:
        raise SecretBoxNotConfiguredError(
            "TENANT_ENCRYPTION_MASTER_KEY is still set to the dev "
            "placeholder. Generate a real Fernet key (see secret_box.py "
            "docstring) and set TENANT_ENCRYPTION_MASTER_KEY in the "
            "environment."
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as e:
        raise SecretBoxNotConfiguredError(
            f"TENANT_ENCRYPTION_MASTER_KEY is set but invalid: {e}. "
            "Must be a Fernet key (32 url-safe base64-encoded bytes)."
        ) from e


def seal(plaintext: str) -> bytes:
    """Encrypt a UTF-8 string. Returns the raw Fernet token (bytes).

    Raises `SecretBoxNotConfiguredError` (subclass of RuntimeError) if
    the master key is missing / placeholder / malformed; callers should
    catch this and translate to an HTTP 500 with a configuration hint.
    """
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
