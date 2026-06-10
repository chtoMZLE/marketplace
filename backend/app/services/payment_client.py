import httpx

from app.core.config import settings

# Set by lifespan in main.py; falls back to per-request client when None (tests).
_client: httpx.AsyncClient | None = None


async def _post(path: str, **kwargs) -> httpx.Response:
    if _client is not None:
        # shared client already has base_url set in lifespan
        return await _client.post(path, **kwargs)
    async with httpx.AsyncClient(base_url=settings.payment_service_url, timeout=10) as c:
        return await c.post(path, **kwargs)


async def lock_escrow(order_id: str, amount: float, customer_id: str, executor_id: str) -> str:
    resp = await _post(
        "/escrow/lock",
        json={"order_id": order_id, "amount": amount, "customer_id": customer_id, "executor_id": executor_id},
    )
    if resp.status_code == 402:
        raise InsufficientFundsError()
    if resp.status_code >= 400:
        raise PaymentServiceError(f"lock failed: {resp.text}")
    return resp.json()["id"]


async def release_escrow(escrow_id: str) -> None:
    resp = await _post("/escrow/release", json={"escrow_id": escrow_id})
    if resp.status_code >= 400:
        raise PaymentServiceError(f"release failed: {resp.text}")


async def refund_escrow(escrow_id: str) -> None:
    resp = await _post("/escrow/refund", json={"escrow_id": escrow_id})
    if resp.status_code >= 400:
        raise PaymentServiceError(f"refund failed: {resp.text}")


async def dispute_escrow(escrow_id: str) -> None:
    resp = await _post("/escrow/dispute", json={"escrow_id": escrow_id})
    if resp.status_code >= 400:
        raise PaymentServiceError(f"dispute failed: {resp.text}")


async def deposit_balance(user_id: str, amount: float) -> None:
    resp = await _post("/balance/deposit", json={"user_id": user_id, "amount": amount})
    if resp.status_code >= 400:
        raise PaymentServiceError(f"deposit failed: {resp.text}")


class InsufficientFundsError(Exception):
    pass


class PaymentServiceError(Exception):
    pass
