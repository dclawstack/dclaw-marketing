"""Legacy v1 campaigns router — Org-scoped as of Sprint 3 (SP3-1).

Every request now carries `?organization_id=...`. Auth is handled by the
test override in conftest.py which injects a superuser into
`current_active_user`.
"""

import pytest


@pytest.mark.asyncio
async def test_create_campaign(auth_client, test_org_id):
    payload = {
        "name": "Summer Sale",
        "type": "email",
        "status": "draft",
        "budget": 5000.0,
        "description": "Email campaign for summer",
    }
    response = await auth_client.post(
        f"/api/v1/campaigns/?organization_id={test_org_id}", json=payload
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Summer Sale"
    assert data["type"] == "email"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_campaigns_scoped_to_org(auth_client, test_org_id):
    await auth_client.post(
        f"/api/v1/campaigns/?organization_id={test_org_id}",
        json={"name": "Test Campaign", "type": "social", "status": "active"},
    )
    response = await auth_client.get(f"/api/v1/campaigns/?organization_id={test_org_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(c["name"] == "Test Campaign" for c in data["items"])


@pytest.mark.asyncio
async def test_get_campaign(auth_client, test_org_id):
    create_resp = await auth_client.post(
        f"/api/v1/campaigns/?organization_id={test_org_id}",
        json={"name": "Detail Campaign", "type": "email", "status": "draft"},
    )
    cid = create_resp.json()["id"]
    response = await auth_client.get(
        f"/api/v1/campaigns/{cid}?organization_id={test_org_id}"
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Detail Campaign"


@pytest.mark.asyncio
async def test_update_campaign(auth_client, test_org_id):
    create_resp = await auth_client.post(
        f"/api/v1/campaigns/?organization_id={test_org_id}",
        json={"name": "Old name", "type": "email", "status": "draft"},
    )
    cid = create_resp.json()["id"]
    response = await auth_client.patch(
        f"/api/v1/campaigns/{cid}?organization_id={test_org_id}",
        json={"name": "New name"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New name"


@pytest.mark.asyncio
async def test_delete_campaign(auth_client, test_org_id):
    create_resp = await auth_client.post(
        f"/api/v1/campaigns/?organization_id={test_org_id}",
        json={"name": "To delete", "type": "email", "status": "draft"},
    )
    cid = create_resp.json()["id"]
    response = await auth_client.delete(
        f"/api/v1/campaigns/{cid}?organization_id={test_org_id}"
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_get_campaign_in_wrong_org_is_404(auth_client, test_org_id):
    """Cross-tenant safety check: a campaign created under org A is
    invisible from org B."""
    create_resp = await auth_client.post(
        f"/api/v1/campaigns/?organization_id={test_org_id}",
        json={"name": "Secret", "type": "email", "status": "draft"},
    )
    cid = create_resp.json()["id"]

    from uuid import uuid4
    other_org_id = str(uuid4())  # not seeded; superuser bypasses member check

    response = await auth_client.get(
        f"/api/v1/campaigns/{cid}?organization_id={other_org_id}"
    )
    assert response.status_code == 404
