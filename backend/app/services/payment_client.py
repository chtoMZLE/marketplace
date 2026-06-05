import httpx

from app.core.config import settings


async def lock_escrow(order_id: str, amount: float, customer_id: str, executor_id: str) -> str:
    """Returns escrow_id on success; raises on failure."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{settings.payment_service_url}/escrow/lock",
            json={"order_id": order_id, "amount": amount, "customer_id": customer_id, "executor_id": executor_id},
        )
    if resp.status_code == 402:
        raise InsufficientFundsError()
    if resp.status_code >= 400:
        raise PaymentServiceError(f"lock failed: {resp.text}")
    return resp.json()["id"]


async def release_escrow(escrow_id: str) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{settings.payment_service_url}/escrow/release",
            json={"escrow_id": escrow_id},
        )
    if resp.status_code >= 400:
        raise PaymentServiceError(f"release failed: {resp.text}")


async def refund_escrow(escrow_id: str) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{settings.payment_service_url}/escrow/refund",
            json={"escrow_id": escrow_id},
        )
    if resp.status_code >= 400:
        raise PaymentServiceError(f"refund failed: {resp.text}")


class InsufficientFundsError(Exception):
    pass


class PaymentServiceError(Exception):
    pass
