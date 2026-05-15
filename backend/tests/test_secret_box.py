"""Unit tests for secret_box configuration-error path (#360)."""

import pytest

from app.core.config import settings
from app.services.secret_box import (
    SecretBoxNotConfiguredError,
    seal,
)


def test_seal_with_placeholder_key_raises_clean_error(monkeypatch):
    monkeypatch.setattr(
        settings,
        "tenant_encryption_master_key",
        "change-me-fernet-master-key-base64==",
    )
    with pytest.raises(SecretBoxNotConfiguredError) as exc:
        seal("anything")
    assert "placeholder" in str(exc.value).lower()


def test_seal_with_empty_key_raises_clean_error(monkeypatch):
    monkeypatch.setattr(settings, "tenant_encryption_master_key", "")
    with pytest.raises(SecretBoxNotConfiguredError) as exc:
        seal("anything")
    assert "unset" in str(exc.value).lower()


def test_seal_with_invalid_key_raises_clean_error(monkeypatch):
    monkeypatch.setattr(
        settings, "tenant_encryption_master_key", "not-a-real-fernet-key"
    )
    with pytest.raises(SecretBoxNotConfiguredError) as exc:
        seal("anything")
    msg = str(exc.value).lower()
    assert "invalid" in msg or "fernet" in msg


def test_seal_with_valid_key_round_trips(monkeypatch):
    from cryptography.fernet import Fernet
    from app.services.secret_box import unseal

    key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "tenant_encryption_master_key", key)
    sealed = seal("hello world")
    assert isinstance(sealed, bytes)
    assert unseal(sealed) == "hello world"
