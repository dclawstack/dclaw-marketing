import pytest
from uuid import uuid4


@pytest.mark.asyncio
async def test_create_lead(client):
    payload = {
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "company": "Acme",
        "source": "website",
        "status": "new",
    }
    response = await client.post("/api/v1/leads/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "john@example.com"
    assert data["first_name"] == "John"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_lead_duplicate_email(client):
    payload = {"email": "dup@example.com", "status": "new"}
    response1 = await client.post("/api/v1/leads/", json=payload)
    assert response1.status_code == 201
    response2 = await client.post("/api/v1/leads/", json=payload)
    assert response2.status_code == 409


@pytest.mark.asyncio
async def test_list_leads(client):
    await client.post("/api/v1/leads/", json={
        "email": "list1@example.com",
        "status": "new",
    })
    response = await client.get("/api/v1/leads/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_list_leads_with_filters(client):
    await client.post("/api/v1/leads/", json={
        "email": "filter@example.com",
        "source": "ads",
        "status": "qualified",
    })
    response = await client.get("/api/v1/leads/?source=ads&status=qualified")
    assert response.status_code == 200
    data = response.json()
    assert all(item["source"] == "ads" for item in data["items"])
    assert all(item["status"] == "qualified" for item in data["items"])


@pytest.mark.asyncio
async def test_list_leads_search(client):
    await client.post("/api/v1/leads/", json={
        "email": "searchable@example.com",
        "first_name": "Alice",
        "status": "new",
    })
    response = await client.get("/api/v1/leads/?search=Alice")
    assert response.status_code == 200
    data = response.json()
    assert any("Alice" in (item.get("first_name") or "") for item in data["items"])


@pytest.mark.asyncio
async def test_get_lead(client):
    create_resp = await client.post("/api/v1/leads/", json={
        "email": "get@example.com",
        "status": "new",
    })
    lead_id = create_resp.json()["id"]
    response = await client.get(f"/api/v1/leads/{lead_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "get@example.com"


@pytest.mark.asyncio
async def test_get_lead_not_found(client):
    response = await client.get(f"/api/v1/leads/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_lead(client):
    create_resp = await client.post("/api/v1/leads/", json={
        "email": "update@example.com",
        "status": "new",
    })
    lead_id = create_resp.json()["id"]
    response = await client.patch(f"/api/v1/leads/{lead_id}", json={
        "first_name": "Updated",
        "status": "contacted",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["status"] == "contacted"


@pytest.mark.asyncio
async def test_delete_lead(client):
    create_resp = await client.post("/api/v1/leads/", json={
        "email": "delete@example.com",
        "status": "new",
    })
    lead_id = create_resp.json()["id"]
    response = await client.delete(f"/api/v1/leads/{lead_id}")
    assert response.status_code == 204
    get_resp = await client.get(f"/api/v1/leads/{lead_id}")
    assert get_resp.status_code == 404
