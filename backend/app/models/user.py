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
from sqlalchemy import Boolean, DateTime, String
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
