import pytest
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_create_analytics_event(client):
    # Create a campaign first
    campaign_resp = await client.post("/api/v1/campaigns/", json={
        "name": "Analytics Campaign",
        "type": "email",
        "status": "active",
    })
    campaign_id = campaign_resp.json()["id"]

    payload = {
        "campaign_id": str(campaign_id),
        "event_type": "click",
        "value": 1.5,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    response = await client.post("/api/v1/analytics/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["event_type"] == "click"
    assert data["value"] == 1.5
    assert "id" in data


@pytest.mark.asyncio
async def test_list_analytics_by_campaign(client):
    campaign_resp = await client.post("/api/v1/campaigns/", json={
        "name": "Analytics Campaign 2",
        "type": "social",
        "status": "active",
    })
    campaign_id = campaign_resp.json()["id"]

    await client.post("/api/v1/analytics/", json={
        "campaign_id": str(campaign_id),
        "event_type": "impression",
        "value": 0.0,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })

    response = await client.get(f"/api/v1/analytics/campaign/{campaign_id}")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_analytics_summary(client):
    campaign_resp = await client.post("/api/v1/campaigns/", json={
        "name": "Summary Campaign",
        "type": "ppc",
        "status": "active",
    })
    campaign_id = campaign_resp.json()["id"]

    await client.post("/api/v1/analytics/", json={
        "campaign_id": str(campaign_id),
        "event_type": "conversion",
        "value": 100.0,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })

    response = await client.get(f"/api/v1/analytics/campaign/{campaign_id}/summary")
    assert response.status_code == 200
    data = response.json()
    assert "conversion" in data
    assert data["conversion"]["count"] >= 1
    assert data["conversion"]["total_value"] >= 100.0
