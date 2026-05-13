from uuid import uuid4

import pytest_asyncio
from fastapi import Request
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


async def override_current_active_user(request: "Request") -> User:
    """Resolve the calling user.

    - If the request carries an Authorization: Bearer <jwt> header, decode
      the token via the configured JWT strategy and return that user.
      This is the path the pre-existing tests rely on — they log in as
      alice/bob/admin and expect per-role responses.
    - Otherwise, return the seeded test superuser. This is the fallback
      for the new SP3-1 tests that don't bring their own JWT.
    """
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        from app.auth.backend import get_jwt_strategy
        from app.auth.manager import get_user_manager

        strategy = get_jwt_strategy()
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            from app.auth.db import get_user_db

            user_db_gen = get_user_db(session).__aiter__()
            user_db = await user_db_gen.__anext__()
            user_mgr_gen = get_user_manager(user_db).__aiter__()
            user_mgr = await user_mgr_gen.__anext__()
            try:
                user = await strategy.read_token(token, user_mgr)
            except Exception:
                user = None
            if user is not None and user.is_active:
                # Detach + reattach in a clean session so the route can use it.
                return user

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
            email="test-superuser@example.com",
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
