"""Legacy v1 analytics router — Org-scoped as of Sprint 3 (SP3-1)."""

from datetime import datetime, timezone

import pytest


@pytest.mark.asyncio
async def test_create_analytics_event(client, test_org_id):
    campaign_resp = await client.post(
        f"/api/v1/campaigns/?organization_id={test_org_id}",
        json={"name": "Analytics Campaign", "type": "email", "status": "active"},
    )
    campaign_id = campaign_resp.json()["id"]

    payload = {
        "campaign_id": str(campaign_id),
        "event_type": "click",
        "value": 1.5,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    response = await client.post(
        f"/api/v1/analytics/?organization_id={test_org_id}", json=payload
    )
    assert response.status_code == 201
    data = response.json()
    assert data["event_type"] == "click"
    assert data["value"] == 1.5


@pytest.mark.asyncio
async def test_list_analytics_by_campaign(client, test_org_id):
    campaign_resp = await client.post(
        f"/api/v1/campaigns/?organization_id={test_org_id}",
        json={"name": "Analytics Campaign 2", "type": "social", "status": "active"},
    )
    campaign_id = campaign_resp.json()["id"]

    await client.post(
        f"/api/v1/analytics/?organization_id={test_org_id}",
        json={
            "campaign_id": str(campaign_id),
            "event_type": "impression",
            "value": 0.0,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    response = await client.get(
        f"/api/v1/analytics/campaign/{campaign_id}?organization_id={test_org_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_analytics_summary(client, test_org_id):
    campaign_resp = await client.post(
        f"/api/v1/campaigns/?organization_id={test_org_id}",
        json={"name": "Summary Campaign", "type": "ppc", "status": "active"},
    )
    campaign_id = campaign_resp.json()["id"]

    await client.post(
        f"/api/v1/analytics/?organization_id={test_org_id}",
        json={
            "campaign_id": str(campaign_id),
            "event_type": "conversion",
            "value": 100.0,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    response = await client.get(
        f"/api/v1/analytics/campaign/{campaign_id}/summary"
        f"?organization_id={test_org_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert "conversion" in data
    assert data["conversion"]["count"] >= 1
    assert data["conversion"]["total_value"] >= 100.0
