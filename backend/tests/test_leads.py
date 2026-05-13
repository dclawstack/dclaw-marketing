"""Legacy v1 leads router — Org-scoped as of Sprint 3 (SP3-1)."""

import pytest


@pytest.mark.asyncio
async def test_create_lead(auth_client, test_org_id):
    payload = {"email": "lead@example.com", "status": "new"}
    response = await auth_client.post(
        f"/api/v1/leads/?organization_id={test_org_id}", json=payload
    )
    assert response.status_code == 201
    assert response.json()["email"] == "lead@example.com"


@pytest.mark.asyncio
async def test_create_duplicate_lead_within_org_409(auth_client, test_org_id):
    payload = {"email": "dup@example.com", "status": "new"}
    r1 = await auth_client.post(
        f"/api/v1/leads/?organization_id={test_org_id}", json=payload
    )
    assert r1.status_code == 201
    r2 = await auth_client.post(
        f"/api/v1/leads/?organization_id={test_org_id}", json=payload
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_list_leads_scoped(auth_client, test_org_id):
    await auth_client.post(
        f"/api/v1/leads/?organization_id={test_org_id}",
        json={"email": "l1@example.com", "status": "new"},
    )
    response = await auth_client.get(f"/api/v1/leads/?organization_id={test_org_id}")
    assert response.status_code == 200
    assert response.json()["total"] >= 1


@pytest.mark.asyncio
async def test_update_lead(auth_client, test_org_id):
    create = await auth_client.post(
        f"/api/v1/leads/?organization_id={test_org_id}",
        json={"email": "upd@example.com", "status": "new"},
    )
    lid = create.json()["id"]
    response = await auth_client.patch(
        f"/api/v1/leads/{lid}?organization_id={test_org_id}",
        json={"status": "qualified"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "qualified"


@pytest.mark.asyncio
async def test_delete_lead(auth_client, test_org_id):
    create = await auth_client.post(
        f"/api/v1/leads/?organization_id={test_org_id}",
        json={"email": "del@example.com", "status": "new"},
    )
    lid = create.json()["id"]
    response = await auth_client.delete(
        f"/api/v1/leads/{lid}?organization_id={test_org_id}"
    )
    assert response.status_code == 204
