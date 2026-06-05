import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _auth(client: AsyncClient, email: str, role: str) -> str:
    await client.post("/register", json={"email": email, "password": "password123", "role": role})
    tokens = (await client.post("/login", json={"email": email, "password": "password123"})).json()
    return tokens["access_token"]


async def test_executor_can_create_service(client: AsyncClient):
    token = await _auth(client, "exec@example.com", "executor")
    resp = await client.post(
        "/services",
        json={"title": "Test", "description": "Desc", "price": 100.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "Test"


async def test_customer_cannot_create_service(client: AsyncClient):
    token = await _auth(client, "cust@example.com", "customer")
    resp = await client.post(
        "/services",
        json={"title": "Test", "description": "Desc", "price": 100.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


async def test_list_services(client: AsyncClient):
    token = await _auth(client, "exec2@example.com", "executor")
    await client.post(
        "/services",
        json={"title": "Svc", "description": "D", "price": 50.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.get("/services")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
