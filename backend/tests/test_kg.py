"""Q3 Knowledge Graph tests — embedding service + KG search + stats."""

import pytest
from fastapi_users.password import PasswordHelper
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ingestion import (
    DocumentChunk,
    IngestionSource,
    IngestionSourceType,
    IngestionStatus,
)
from app.models.organization import Organization, OrganizationMembership, OrganizationRole
from app.models.user import User
from app.services.embeddings import (
    EMBEDDING_DIM,
    _stub_embedding,
    embed_text,
    embed_texts,
    is_real_provider_configured,
)
from tests.conftest import test_engine


_helper = PasswordHelper()


# ---------- service layer ----------------------------------------------

def test_stub_embedding_dim_matches_column():
    vec = _stub_embedding("hello world")
    assert len(vec) == EMBEDDING_DIM


def test_stub_embedding_deterministic():
    a = _stub_embedding("same text")
    b = _stub_embedding("same text")
    assert a == b


def test_stub_embedding_different_inputs_produce_different_vectors():
    a = _stub_embedding("text one")
    b = _stub_embedding("text two completely different")
    assert a != b


@pytest.mark.asyncio
async def test_embed_text_uses_stub_when_no_api_key():
    """When openai_api_key is unset (default in tests), embed_text
    falls back to the deterministic stub embedder."""
    assert not is_real_provider_configured()
    vec, model = await embed_text("hello world")
    assert len(vec) == EMBEDDING_DIM
    assert model.startswith("stub/")


@pytest.mark.asyncio
async def test_embed_texts_batched():
    vecs, model = await embed_texts(["one", "two", "three"])
    assert len(vecs) == 3
    assert all(len(v) == EMBEDDING_DIM for v in vecs)


@pytest.mark.asyncio
async def test_embed_texts_empty_list_returns_empty():
    vecs, model = await embed_texts([])
    assert vecs == []


# ---------- KG search route -------------------------------------------

async def _seed_user(email: str, password: str, *, is_superuser: bool = False) -> User:
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        u = User(
            email=email,
            hashed_password=_helper.hash(password),
            is_active=True, is_superuser=is_superuser, is_verified=True,
            full_name="Test", password_reset_required=False,
        )
        session.add(u)
        await session.commit()
        await session.refresh(u)
        return u


async def _seed_org_with(user: User, role: OrganizationRole) -> Organization:
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug="acme", name="ACME")
        session.add(org)
        await session.flush()
        session.add(OrganizationMembership(user_id=user.id, organization_id=org.id, role=role))
        await session.commit()
        await session.refresh(org)
        return org


async def _seed_chunks(org: Organization, texts: list[str]) -> list[DocumentChunk]:
    """Create one IngestionSource + one DocumentChunk per text, with
    deterministic stub embeddings.
    """
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        src = IngestionSource(
            organization_id=org.id,
            source_type=IngestionSourceType.file,
            source_reference="fake-asset-id",
            status=IngestionStatus.ready,
        )
        session.add(src)
        await session.flush()

        chunks = []
        for i, text in enumerate(texts):
            vec = _stub_embedding(text)
            c = DocumentChunk(
                organization_id=org.id,
                source_id=src.id,
                position=i,
                text=text,
                embedding=vec,
                embedding_model="stub/sha256",
            )
            session.add(c)
            chunks.append(c)
        await session.commit()
        for c in chunks:
            await session.refresh(c)
        return chunks


async def _login(client, email: str, password: str) -> str:
    res = await client.post(
        "/api/v1/auth/jwt/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_kg_search_returns_results(client):
    user = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(user, OrganizationRole.creatives)
    await _seed_chunks(org, ["hello world", "foo bar baz", "lorem ipsum"])

    token = await _login(client, "alice@example.com", "AlicePwd123!")
    res = await client.post(
        "/api/v1/kg/search",
        json={
            "organization_id": str(org.id),
            "query": "hello world",
            "top_k": 5,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["query"] == "hello world"
    assert len(body["results"]) == 3
    # First result should be the exact-match "hello world" since stub
    # embedding is deterministic on input.
    assert body["results"][0]["text"] == "hello world"
    # Similarity scores in range
    for r in body["results"]:
        assert -1.0 <= r["similarity"] <= 1.0


@pytest.mark.asyncio
async def test_kg_search_top_k_limit(client):
    user = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(user, OrganizationRole.creatives)
    await _seed_chunks(org, [f"chunk {i}" for i in range(20)])

    token = await _login(client, "alice@example.com", "AlicePwd123!")
    res = await client.post(
        "/api/v1/kg/search",
        json={"organization_id": str(org.id), "query": "chunk 5", "top_k": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert len(res.json()["results"]) == 3


@pytest.mark.asyncio
async def test_kg_search_org_scoped(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(alice, OrganizationRole.creatives)
    # Make a 2nd org with chunks; alice should NOT see them.
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org2 = Organization(slug="rival", name="RIVAL")
        session.add(org2)
        await session.flush()
        await session.commit()
        await session.refresh(org2)
    await _seed_chunks(org, ["my-org-secret-content"])
    await _seed_chunks(org2, ["other-org-secret-content"])

    token = await _login(client, "alice@example.com", "AlicePwd123!")
    res = await client.post(
        "/api/v1/kg/search",
        json={
            "organization_id": str(org.id),
            "query": "secret content",
            "top_k": 10,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    texts = [r["text"] for r in res.json()["results"]]
    assert "my-org-secret-content" in texts
    assert "other-org-secret-content" not in texts


@pytest.mark.asyncio
async def test_kg_search_non_member_403(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(alice, OrganizationRole.admin)
    await _seed_chunks(org, ["secret"])
    await _seed_user("intruder@example.com", "IntPwd1234567!")

    token = await _login(client, "intruder@example.com", "IntPwd1234567!")
    res = await client.post(
        "/api/v1/kg/search",
        json={"organization_id": str(org.id), "query": "secret", "top_k": 10},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_kg_stats(client):
    user = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(user, OrganizationRole.creatives)
    await _seed_chunks(org, ["a", "b", "c"])

    token = await _login(client, "alice@example.com", "AlicePwd123!")
    res = await client.get(
        f"/api/v1/kg/stats?organization_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["chunk_count"] == 3
    assert body["embedded_count"] == 3
    assert body["source_count"] == 1


@pytest.mark.asyncio
async def test_kg_search_excludes_chunks_without_embeddings(client):
    user = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(user, OrganizationRole.creatives)

    # Manually add a chunk without an embedding
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        src = IngestionSource(
            organization_id=org.id,
            source_type=IngestionSourceType.file,
            source_reference="x",
            status=IngestionStatus.ready,
        )
        session.add(src)
        await session.flush()
        # one embedded, one not
        session.add(DocumentChunk(
            organization_id=org.id, source_id=src.id, position=0,
            text="with embedding", embedding=_stub_embedding("with embedding"),
            embedding_model="stub/sha256",
        ))
        session.add(DocumentChunk(
            organization_id=org.id, source_id=src.id, position=1,
            text="without embedding",
        ))
        await session.commit()

    token = await _login(client, "alice@example.com", "AlicePwd123!")
    res = await client.post(
        "/api/v1/kg/search",
        json={"organization_id": str(org.id), "query": "embedding", "top_k": 10},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    texts = [r["text"] for r in res.json()["results"]]
    assert "with embedding" in texts
    assert "without embedding" not in texts
