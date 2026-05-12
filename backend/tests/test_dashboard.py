"""Legacy /api/v1/dashboard — Org-scoped as of Sprint 3 (SP3-1)."""

import pytest


@pytest.mark.asyncio
async def test_dashboard_stats(client, test_org_id):
    await client.post(
        f"/api/v1/campaigns/?organization_id={test_org_id}",
        json={"name": "Active Campaign", "type": "email", "status": "active"},
    )
    await client.post(
        f"/api/v1/leads/?organization_id={test_org_id}",
        json={"email": "dash@example.com", "status": "converted"},
    )

    response = await client.get(f"/api/v1/dashboard?organization_id={test_org_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["organization_id"] == test_org_id
    assert "active_campaigns" in data
    assert "total_leads" in data
    assert "conversion_rate" in data
    assert "total_spend" in data
    assert data["active_campaigns"] >= 1
    assert data["total_leads"] >= 1
