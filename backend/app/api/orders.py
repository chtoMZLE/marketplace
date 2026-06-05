from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.order import OrderStatus
from app.models.user import User
from app.schemas.order import OrderCreate, OrderOut
from app.services.order_service import create_order, get_order, get_orders_for_user, set_status
from app.services.payment_client import InsufficientFundsError, PaymentServiceError, lock_escrow, refund_escrow, release_escrow
from app.services.service_service import get_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create(
    data: OrderCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = await get_service(db, data.service_id)
    if not svc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    import uuid
    temp_order_id = str(uuid.uuid4())

    try:
        escrow_id = await lock_escrow(
            order_id=temp_order_id,
            amount=float(svc.price),
            customer_id=current_user.id,
            executor_id=svc.executor_id,
        )
    except InsufficientFundsError:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient balance")
    except PaymentServiceError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payment service unavailable")

    return await create_order(db, data.service_id, current_user.id, escrow_id)


@router.post("/{order_id}/accept", response_model=OrderOut)
async def accept(
    order_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    order = await _get_or_404(db, order_id)
    svc = await get_service(db, order.service_id)
    if svc.executor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the executor of this service")
    if order.status != OrderStatus.pending:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order is not in pending status")
    return await set_status(db, order, OrderStatus.active)


@router.post("/{order_id}/complete", response_model=OrderOut)
async def complete(
    order_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    order = await _get_or_404(db, order_id)
    if order.customer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the customer")
    if order.status != OrderStatus.active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order is not in active status")

    try:
        await release_escrow(order.escrow_tx_id)
    except PaymentServiceError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payment service unavailable")

    return await set_status(db, order, OrderStatus.completed)


@router.post("/{order_id}/dispute", response_model=OrderOut)
async def dispute(
    order_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    order = await _get_or_404(db, order_id)
    svc = await get_service(db, order.service_id)
    is_party = order.customer_id == current_user.id or svc.executor_id == current_user.id
    if not is_party:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a party to this order")
    if order.status not in (OrderStatus.pending, OrderStatus.active):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot dispute in current status")
    return await set_status(db, order, OrderStatus.disputed)


@router.post("/{order_id}/cancel", response_model=OrderOut)
async def cancel(
    order_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    order = await _get_or_404(db, order_id)
    if order.customer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the customer")
    if order.status != OrderStatus.pending:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only pending orders can be cancelled")

    try:
        await refund_escrow(order.escrow_tx_id)
    except PaymentServiceError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payment service unavailable")

    return await set_status(db, order, OrderStatus.cancelled)


@router.get("", response_model=list[OrderOut])
async def list_orders(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_orders_for_user(db, current_user.id)


@router.get("/{order_id}", response_model=OrderOut)
async def get_one(
    order_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await _get_or_404(db, order_id)


async def _get_or_404(db: AsyncSession, order_id: str):
    order = await get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order
