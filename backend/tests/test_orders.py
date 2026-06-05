from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _auth(client: AsyncClient, email: str, role: str) -> tuple[str, dict]:
    resp = await client.post("/register", json={"email": email, "password": "password123", "role": role})
    user = resp.json()
    tokens = (await client.post("/login", json={"email": email, "password": "password123"})).json()
    return tokens["access_token"], user


async def _create_service(client: AsyncClient, token: str, price: float = 100.0) -> dict:
    resp = await client.post(
        "/services",
        json={"title": "Svc", "description": "D", "price": price},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


async def test_order_full_flow(client: AsyncClient):
    exec_token, exec_user = await _auth(client, "exec_flow@example.com", "executor")
    cust_token, cust_user = await _auth(client, "cust_flow@example.com", "customer")
    svc = await _create_service(client, exec_token, 50.0)

    with patch("app.api.orders.lock_escrow", new_callable=AsyncMock, return_value="escrow-001"), \
         patch("app.api.orders.release_escrow", new_callable=AsyncMock):

        # Create order
        resp = await client.post(
            "/orders", json={"service_id": svc["id"]},
            headers={"Authorization": f"Bearer {cust_token}"}
        )
        assert resp.status_code == 201, resp.text
        order = resp.json()
        assert order["status"] == "pending"

        # Accept
        resp = await client.post(
            f"/orders/{order['id']}/accept",
            headers={"Authorization": f"Bearer {exec_token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

        # Complete
        resp = await client.post(
            f"/orders/{order['id']}/complete",
            headers={"Authorization": f"Bearer {cust_token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"


async def test_order_zero_balance_returns_402(client: AsyncClient):
    exec_token, _ = await _auth(client, "exec_bal@example.com", "executor")
    cust_token, _ = await _auth(client, "cust_bal@example.com", "customer")
    svc = await _create_service(client, exec_token, 100.0)

    from app.services.payment_client import InsufficientFundsError

    with patch("app.api.orders.lock_escrow", new_callable=AsyncMock, side_effect=InsufficientFundsError()):
        resp = await client.post(
            "/orders", json={"service_id": svc["id"]},
            headers={"Authorization": f"Bearer {cust_token}"}
        )
    assert resp.status_code == 402


async def test_order_dispute(client: AsyncClient):
    exec_token, _ = await _auth(client, "exec_disp@example.com", "executor")
    cust_token, _ = await _auth(client, "cust_disp@example.com", "customer")
    svc = await _create_service(client, exec_token)

    with patch("app.api.orders.lock_escrow", new_callable=AsyncMock, return_value="escrow-002"):
        resp = await client.post(
            "/orders", json={"service_id": svc["id"]},
            headers={"Authorization": f"Bearer {cust_token}"}
        )
        order = resp.json()

    resp = await client.post(
        f"/orders/{order['id']}/dispute",
        headers={"Authorization": f"Bearer {cust_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "disputed"


async def test_cancel_pending_order(client: AsyncClient):
    exec_token, _ = await _auth(client, "exec_cancel@example.com", "executor")
    cust_token, _ = await _auth(client, "cust_cancel@example.com", "customer")
    svc = await _create_service(client, exec_token)

    with patch("app.api.orders.lock_escrow", new_callable=AsyncMock, return_value="escrow-003"), \
         patch("app.api.orders.refund_escrow", new_callable=AsyncMock):

        resp = await client.post(
            "/orders", json={"service_id": svc["id"]},
            headers={"Authorization": f"Bearer {cust_token}"}
        )
        order = resp.json()

        resp = await client.post(
            f"/orders/{order['id']}/cancel",
            headers={"Authorization": f"Bearer {cust_token}"}
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


async def test_get_orders_history(client: AsyncClient):
    exec_token, _ = await _auth(client, "exec_hist@example.com", "executor")
    cust_token, _ = await _auth(client, "cust_hist@example.com", "customer")
    svc = await _create_service(client, exec_token)

    with patch("app.api.orders.lock_escrow", new_callable=AsyncMock, return_value="escrow-004"):
        await client.post(
            "/orders", json={"service_id": svc["id"]},
            headers={"Authorization": f"Bearer {cust_token}"}
        )

    resp = await client.get("/orders", headers={"Authorization": f"Bearer {cust_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
