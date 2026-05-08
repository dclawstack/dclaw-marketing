import pytest
from uuid import uuid4

from app.models.campaign import Campaign, CampaignType, CampaignStatus


@pytest.mark.asyncio
async def test_create_campaign(client):
    payload = {
        "name": "Summer Sale",
        "type": "email",
        "status": "draft",
        "budget": 5000.0,
        "description": "Email campaign for summer",
    }
    response = await client.post("/api/v1/campaigns/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Summer Sale"
    assert data["type"] == "email"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_campaigns(client):
    # Create a campaign first
    await client.post("/api/v1/campaigns/", json={
        "name": "Test Campaign",
        "type": "social",
        "status": "active",
    })
    response = await client.get("/api/v1/campaigns/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_list_campaigns_with_filters(client):
    await client.post("/api/v1/campaigns/", json={
        "name": "Filtered Campaign",
        "type": "ppc",
        "status": "paused",
    })
    response = await client.get("/api/v1/campaigns/?status=paused&type=ppc")
    assert response.status_code == 200
    data = response.json()
    assert all(item["status"] == "paused" for item in data["items"])
    assert all(item["type"] == "ppc" for item in data["items"])


@pytest.mark.asyncio
async def test_get_campaign(client):
    create_resp = await client.post("/api/v1/campaigns/", json={
        "name": "Detail Campaign",
        "type": "content",
        "status": "draft",
    })
    campaign_id = create_resp.json()["id"]
    response = await client.get(f"/api/v1/campaigns/{campaign_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Detail Campaign"
    assert "lead_count" in data


@pytest.mark.asyncio
async def test_get_campaign_not_found(client):
    response = await client.get(f"/api/v1/campaigns/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_campaign(client):
    create_resp = await client.post("/api/v1/campaigns/", json={
        "name": "Update Me",
        "type": "email",
        "status": "draft",
    })
    campaign_id = create_resp.json()["id"]
    response = await client.patch(f"/api/v1/campaigns/{campaign_id}", json={
        "name": "Updated Name",
        "status": "active",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_delete_campaign(client):
    create_resp = await client.post("/api/v1/campaigns/", json={
        "name": "Delete Me",
        "type": "social",
        "status": "draft",
    })
    campaign_id = create_resp.json()["id"]
    response = await client.delete(f"/api/v1/campaigns/{campaign_id}")
    assert response.status_code == 204
    get_resp = await client.get(f"/api/v1/campaigns/{campaign_id}")
    assert get_resp.status_code == 404
