"""User model — extends FastAPI-Users' SQLAlchemy base.

The base provides: id (UUID), email, hashed_password, is_active,
is_superuser, is_verified. We add:

- full_name: displayed in UI
- password_reset_required: TRUE for admin-created users; flips to
  FALSE after the user completes the mandatory first-login reset.
- created_at / updated_at: standard timestamp pair.

Admin role is represented by FastAPI-Users' is_superuser flag.
Project- and Organization-scoped roles live in the membership tables.
"""

from datetime import datetime, timezone

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Forces a password reset on the next login. Admin-created users have
    # this set to True; resets to False once /me/password is used.
    password_reset_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # A.11.6 — opt-in TOTP 2FA. `totp_secret` is the Fernet-sealed base32
    # secret; null = not enrolled. `totp_enabled` flips True after the
    # user submits a verification code that proves they scanned the QR.
    totp_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # Sprint 4 — full user slug: `u-{first4(name)}-{random6hex}`.
    # Bootstrap superadmin is `s-admn-000000` (s- prefix reserved).
    # Generated at insert time via app.services.slugs.make_slug.
    slug: Mapped[str | None] = mapped_column(
        String(32), nullable=True, unique=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
