import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def register(client: AsyncClient, email: str, role: str = "customer") -> dict:
    resp = await client.post("/register", json={"email": email, "password": "password123", "role": role})
    return resp


async def login(client: AsyncClient, email: str, password: str = "password123") -> dict:
    resp = await client.post("/login", json={"email": email, "password": password})
    return resp


async def test_register_new_user(client: AsyncClient):
    resp = await register(client, "user@example.com")
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "user@example.com"
    assert data["role"] == "customer"


async def test_register_duplicate_email(client: AsyncClient):
    await register(client, "dup@example.com")
    resp = await register(client, "dup@example.com")
    assert resp.status_code == 409


async def test_login_valid_credentials(client: AsyncClient):
    await register(client, "login@example.com")
    resp = await login(client, "login@example.com")
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert "refresh_token" in resp.json()


async def test_login_invalid_credentials(client: AsyncClient):
    await register(client, "bad@example.com")
    resp = await login(client, "bad@example.com", "wrongpassword")
    assert resp.status_code == 401


async def test_me_authenticated(client: AsyncClient):
    await register(client, "me@example.com")
    tokens = (await login(client, "me@example.com")).json()
    resp = await client.get("/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"


async def test_token_refresh(client: AsyncClient):
    await register(client, "refresh@example.com")
    tokens = (await login(client, "refresh@example.com")).json()
    resp = await client.post("/token/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
