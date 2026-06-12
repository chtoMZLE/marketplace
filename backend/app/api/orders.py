import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.order import OrderStatus
from app.models.service import ServiceStatus
from app.models.user import User
from app.schemas.order import OrderCreate, OrderOut
from app.services.order_service import create_order, get_order, get_orders_for_user, set_status
from app.services.payment_client import (
    InsufficientFundsError,
    PaymentServiceError,
    dispute_escrow,
    lock_escrow,
    refund_escrow,
    release_escrow,
)
from app.services.service_service import get_service
from app.services.user_service import get_user_by_id, update_balance

router = APIRouter(prefix="/orders", tags=["orders"])

_401 = {401: {"description": "Не авторизован"}}
_403 = {403: {"description": "Недостаточно прав"}}
_404 = {404: {"description": "Заказ не найден"}}
_409 = {409: {"description": "Недопустимый переход статуса"}}
_503 = {503: {"description": "Платёжный микросервис недоступен"}}


@router.post(
    "",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создать заказ",
    description=(
        "Создаёт заказ и блокирует стоимость услуги в эскроу. "
        "Требует наличия достаточного баланса у покупателя. "
        "При сбое DB-записи средства автоматически возвращаются."
    ),
    responses={
        **_401,
        402: {"description": "Недостаточно средств на балансе"},
        404: {"description": "Услуга не найдена"},
        **_503,
    },
)
async def create(
    data: OrderCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = await get_service(db, data.service_id)
    if not svc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Услуга не найдена")
    if svc.status != ServiceStatus.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Услуга недоступна для заказа")

    temp_order_id = str(uuid.uuid4())

    try:
        escrow_id = await lock_escrow(
            order_id=temp_order_id,
            amount=float(svc.price),
            customer_id=current_user.id,
            executor_id=svc.executor_id,
        )
    except InsufficientFundsError:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Недостаточно средств на балансе"
        ) from None
    except PaymentServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Платёжный сервис недоступен"
        ) from None

    try:
        await update_balance(db, current_user, -float(svc.price))
        return await create_order(db, data.service_id, current_user.id, escrow_id)
    except Exception:
        try:
            await refund_escrow(escrow_id)
            await update_balance(db, current_user, float(svc.price))
        except PaymentServiceError:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить заказ. Средства возвращены на баланс.",
        ) from None


@router.post(
    "/{order_id}/accept",
    response_model=OrderOut,
    summary="Принять заказ",
    description="Исполнитель принимает заказ в работу: статус `pending` → `active`.",
    responses={**_401, **_403, **_404, **_409},
)
async def accept(
    order_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    order = await _get_or_404(db, order_id)
    svc = await get_service(db, order.service_id)
    if svc.executor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь исполнителем этой услуги")
    if order.status != OrderStatus.pending:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Заказ не находится в статусе ожидания")
    return await set_status(db, order, OrderStatus.active)


@router.post(
    "/{order_id}/complete",
    response_model=OrderOut,
    summary="Подтвердить выполнение",
    description=(
        "Покупатель подтверждает, что услуга оказана. "
        "Средства из эскроу переводятся исполнителю: статус `active` → `completed`."
    ),
    responses={**_401, **_403, **_404, **_409, **_503},
)
async def complete(
    order_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    order = await _get_or_404(db, order_id)
    if order.customer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь заказчиком")
    if order.status != OrderStatus.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Подтвердить можно только заказ со статусом 'В работе'",
        )

    try:
        await release_escrow(order.escrow_tx_id)
    except PaymentServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Платёжный сервис недоступен"
        ) from None

    svc = await get_service(db, order.service_id)
    executor = await get_user_by_id(db, svc.executor_id)
    if executor:
        await update_balance(db, executor, float(svc.price))

    return await set_status(db, order, OrderStatus.completed)


@router.post(
    "/{order_id}/dispute",
    response_model=OrderOut,
    summary="Открыть спор",
    description=(
        "Любая из сторон (покупатель или исполнитель) может открыть спор. "
        "Средства остаются заблокированы в эскроу до разрешения."
    ),
    responses={**_401, **_403, **_404, **_409, **_503},
)
async def dispute(
    order_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    order = await _get_or_404(db, order_id)
    svc = await get_service(db, order.service_id)
    is_party = order.customer_id == current_user.id or svc.executor_id == current_user.id
    if not is_party:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь участником этого заказа")
    if order.status not in (OrderStatus.pending, OrderStatus.active):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Спор нельзя открыть в текущем статусе")

    try:
        await dispute_escrow(order.escrow_tx_id)
    except PaymentServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Платёжный сервис недоступен"
        ) from None

    return await set_status(db, order, OrderStatus.disputed)


@router.post(
    "/{order_id}/cancel",
    response_model=OrderOut,
    summary="Отменить заказ",
    description=(
        "Покупатель отменяет заказ в статусе `pending`. "
        "Средства возвращаются с эскроу на баланс покупателя."
    ),
    responses={**_401, **_403, **_404, **_409, **_503},
)
async def cancel(
    order_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    order = await _get_or_404(db, order_id)
    if order.customer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь заказчиком")
    if order.status != OrderStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Отменить можно только заказ в статусе ожидания",
        )

    try:
        await refund_escrow(order.escrow_tx_id)
    except PaymentServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Платёжный сервис недоступен"
        ) from None

    svc = await get_service(db, order.service_id)
    await update_balance(db, current_user, float(svc.price))
    return await set_status(db, order, OrderStatus.cancelled)


@router.get(
    "",
    response_model=list[OrderOut],
    summary="История заказов",
    description="Возвращает все заказы, где текущий пользователь является покупателем или исполнителем.",
    responses=_401,
)
async def list_orders(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_orders_for_user(db, current_user.id)


@router.get(
    "/{order_id}",
    response_model=OrderOut,
    summary="Получить заказ по ID",
    responses={**_401, **_404},
)
async def get_one(
    order_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await _get_or_404(db, order_id)


async def _get_or_404(db: AsyncSession, order_id: str):
    order = await get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    return order
