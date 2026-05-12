"""Connection — encrypted credentials for an MCP server (Theme D / Phase 6).

A Connection binds one Org to one MCP server (by server_id), holding
the encrypted access material plus scope + status metadata. Unlike
SocialAccount (which is publisher-shaped), Connection is the generic
tool-layer container — same model for CRM tokens, ad-platform tokens,
analytics keys, drive auth, etc.
"""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ConnectionStatus(str, enum.Enum):
    active = "active"
    reauth_required = "reauth_required"
    revoked = "revoked"
    error = "error"


class Connection(Base):
    """One Org × one MCP server credential set."""

    __tablename__ = "connections"
    __table_args__ = (
        # Multiple labels per server allowed (e.g. two HubSpot tenants),
        # so uniqueness keys on (org, server_id, name).
        UniqueConstraint(
            "organization_id",
            "server_id",
            "name",
            name="uq_connection_org_server_name",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # The MCP server's stable ID (e.g. "hubspot", "ga4", "linkedin").
    # Resolves to a MCPServerDef in app.services.mcp_registry.
    server_id: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Auth kind ("oauth2" / "pat" / "api_key" / "basic_auth").
    auth_kind: Mapped[str] = mapped_column(String(32), nullable=False)

    # Encrypted secret — Fernet token bytes. Decrypted via
    # app.services.secret_box.unseal at use time.
    encrypted_secret_blob: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True
    )

    # Non-secret metadata that's nice to have plaintext for diagnostics
    # (workspace IDs, account labels, etc.). Never put tokens here.
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scopes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    status: Mapped[ConnectionStatus] = mapped_column(
        SQLEnum(ConnectionStatus),
        nullable=False,
        default=ConnectionStatus.active,
    )
    last_health_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
