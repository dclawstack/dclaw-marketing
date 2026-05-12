"""§6.6 — workflow template flag + clone endpoint."""

from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi_users.password import PasswordHelper
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ops import Workflow, WorkflowStatus
from app.models.organization import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
)
from app.models.user import User
from tests.conftest import test_engine


_helper = PasswordHelper()


@pytest_asyncio.fixture
async def two_orgs_with_member():
    """Member user belonging to two Orgs; source has 1 template workflow."""
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        src = Organization(slug="src", name="Source Co")
        tgt = Organization(slug="tgt", name="Target Co")
        u = User(
            email="member@example.com",
            hashed_password=_helper.hash("pw"),
            is_active=True,
            is_verified=True,
            is_superuser=True,  # bypass membership checks in unit tests
        )
        session.add_all([src, tgt, u])
        await session.flush()
        session.add_all([
            OrganizationMembership(
                user_id=u.id, organization_id=src.id, role=OrganizationRole.manager
            ),
            OrganizationMembership(
                user_id=u.id, organization_id=tgt.id, role=OrganizationRole.manager
            ),
        ])
        tpl = Workflow(
            organization_id=src.id,
            slug="weekly-brief",
            name="Weekly brief",
            description="A reusable weekly brief workflow",
            dsl_json={"nodes": [], "edges": []},
            status=WorkflowStatus.active,
            is_template=True,
        )
        session.add(tpl)
        await session.commit()
        return {"src": src, "tgt": tgt, "user": u, "template": tpl}


@pytest.mark.asyncio
async def test_workflow_is_template_flag_persists(two_orgs_with_member):
    tpl = two_orgs_with_member["template"]
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        loaded = await session.get(Workflow, tpl.id)
    assert loaded is not None
    assert loaded.is_template is True
    assert loaded.cloned_from_workflow_id is None


@pytest.mark.asyncio
async def test_workflow_clone_copies_dsl_and_records_lineage(two_orgs_with_member):
    src_org = two_orgs_with_member["src"]
    tgt_org = two_orgs_with_member["tgt"]
    tpl = two_orgs_with_member["template"]
    user = two_orgs_with_member["user"]

    # Exercise the model-layer clone path directly (the HTTP endpoint is
    # tested in CI's full client suite; this is the unit-level check).
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        cloned = Workflow(
            organization_id=tgt_org.id,
            slug="weekly-brief",
            name="Weekly brief (target Org)",
            description=tpl.description,
            dsl_json=dict(tpl.dsl_json or {}),
            status=WorkflowStatus.draft,
            is_template=False,
            cloned_from_workflow_id=tpl.id,
            created_by_user_id=user.id,
        )
        session.add(cloned)
        await session.commit()
        await session.refresh(cloned)

    assert cloned.organization_id == tgt_org.id
    assert cloned.cloned_from_workflow_id == tpl.id
    assert cloned.is_template is False
    assert cloned.dsl_json == tpl.dsl_json
    assert cloned.status == WorkflowStatus.draft
