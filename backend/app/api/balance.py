from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.order import BalanceOut, BalanceTopup
from app.services.payment_client import PaymentServiceError, deposit_balance
from app.services.user_service import update_balance

router = APIRouter(prefix="/balance", tags=["balance"])

_401 = {401: {"description": "Не авторизован"}}
_503 = {503: {"description": "Платёжный микросервис недоступен"}}


@router.post(
    "/topup",
    response_model=BalanceOut,
    summary="Пополнение баланса",
    description=(
        "Зачисляет указанную сумму на баланс покупателя. "
        "Сначала обновляет баланс в платёжном микросервисе (Go), затем в основной БД. "
        "Если платёжный сервис недоступен — баланс не меняется."
    ),
    responses={**_401, **_503, 422: {"description": "Сумма должна быть положительной"}},
)
async def topup(
    data: BalanceTopup,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if data.amount <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Сумма должна быть положительной")
    try:
        await deposit_balance(str(current_user.id), float(data.amount))
    except PaymentServiceError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Платёжный сервис недоступен")
    user = await update_balance(db, current_user, data.amount)
    return BalanceOut(balance=float(user.balance))


@router.get(
    "",
    response_model=BalanceOut,
    summary="Текущий баланс",
    description="Возвращает актуальный баланс авторизованного пользователя.",
    responses=_401,
)
async def get_balance(current_user: Annotated[User, Depends(get_current_user)]):
    return BalanceOut(balance=float(current_user.balance))
