from uuid import uuid4

import pytest_asyncio
from fastapi_users.password import PasswordHelper
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool

from app.api.main import app
from app.auth import current_active_user
from app.core.database import get_db
from app.models.base import Base
from app.models.organization import Organization
from app.models.user import User

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/dclaw_app_test"

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)


# Holds the test superuser used to satisfy `current_active_user` in
# legacy / unauthenticated tests. Refreshed per setup_db cycle.
_TEST_SUPERUSER: dict[str, User | None] = {"user": None}


async def override_get_db():
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        try:
            yield session
        finally:
            await session.close()


async def override_current_active_user() -> User:
    """Return a pre-seeded superuser; bypasses fastapi-users JWT checks.

    Tests that need a non-superuser identity should re-override this
    dependency in their own scope.
    """
    user = _TEST_SUPERUSER["user"]
    if user is None:
        raise RuntimeError(
            "Test superuser not initialised — setup_db fixture must run first."
        )
    return user


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[current_active_user] = override_current_active_user


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        # pgvector extension — required by DocumentChunk.embedding column
        # (Q3 / Theme Q3 knowledge graph). pgvector/pgvector:pg16 image
        # ships the extension; we just need to enable it for this DB.
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Seed a default superuser so override_current_active_user resolves.
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        helper = PasswordHelper()
        u = User(
            id=uuid4(),
            email="test-superuser@dclaw.local",
            hashed_password=helper.hash("test-pw"),
            is_active=True,
            is_verified=True,
            is_superuser=True,
        )
        session.add(u)
        await session.commit()
        await session.refresh(u)
        _TEST_SUPERUSER["user"] = u

    yield
    _TEST_SUPERUSER["user"] = None
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def test_org_id() -> str:
    """Seed an Organization that legacy-router tests can scope to."""
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug=f"test-org-{uuid4().hex[:8]}", name="Test Org")
        session.add(org)
        await session.commit()
        await session.refresh(org)
        return str(org.id)
