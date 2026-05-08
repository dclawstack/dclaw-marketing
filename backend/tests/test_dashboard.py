import pytest
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_dashboard_stats(client):
    # Create an active campaign
    await client.post("/api/v1/campaigns/", json={
        "name": "Active Campaign",
        "type": "email",
        "status": "active",
    })

    # Create a lead
    await client.post("/api/v1/leads/", json={
        "email": "dash@example.com",
        "status": "converted",
    })

    response = await client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "active_campaigns" in data
    assert "total_leads" in data
    assert "conversion_rate" in data
    assert "total_spend" in data
    assert data["active_campaigns"] >= 1
    assert data["total_leads"] >= 1
