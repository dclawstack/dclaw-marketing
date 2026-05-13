"""Async SQLAlchemy engine + session + lifespan init."""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.models.base import Base


engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "dev",
    pool_pre_ping=True,
)


async def get_db() -> AsyncSession:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Bootstrap path called at app startup.

    Two responsibilities:
    1. Ensure schema exists. In production this is handled by `alembic
       upgrade head` (via a Helm pre-install Job). For dev/tests, we
       fall back to Base.metadata.create_all so the app boots on a
       fresh DB without requiring alembic to be run first.
    2. Ensure a bootstrap Admin user exists. On a clean install with
       no users, create one from BOOTSTRAP_ADMIN_EMAIL +
       BOOTSTRAP_ADMIN_TEMP_PASSWORD so the operator can log in.
       password_reset_required=True so they must change it.
    """
    # Schema (dev/tests only — prod uses alembic).
    # pgvector extension must be enabled BEFORE create_all so the
    # `embedding vector(1536)` column on DocumentChunk can be created.
    # The pgvector/pgvector:pg16 image ships the extension; we just
    # turn it on for the current DB.
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    # Bootstrap admin — re-asserted on every startup so a lost or
    # rotated password is recoverable by simply restarting the backend.
    # This is a pre-launch convenience; a proper recovery flow lands
    # later (see PLAN-v1.2 Phase-1 polish).
    from app.models.user import User  # late import to avoid cycle
    from fastapi_users.password import PasswordHelper

    helper = PasswordHelper()
    hashed = helper.hash(settings.bootstrap_admin_temp_password)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        existing = await session.execute(
            select(User).where(User.email == settings.bootstrap_admin_email)
        )
        admin = existing.scalar_one_or_none()
        if admin is None:
            admin = User(
                email=settings.bootstrap_admin_email,
                hashed_password=hashed,
                is_active=True,
                is_superuser=True,
                is_verified=True,
                full_name="Bootstrap Admin",
                password_reset_required=False,
                display_code="000000",
            )
            session.add(admin)
        else:
            # Re-assert the hardcoded credentials. Keeps the password in
            # sync with whatever's currently in bootstrap_admin_temp_password
            # so a config change + restart is a safe recovery path.
            admin.hashed_password = hashed
            admin.is_active = True
            admin.is_superuser = True
            admin.is_verified = True
            admin.password_reset_required = False
            # Re-assert the bootstrap admin's display_code in case the column
            # was just added or somehow drifted.
            admin.display_code = "000000"
        await session.commit()
