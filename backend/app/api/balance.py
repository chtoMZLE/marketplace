from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.order import BalanceOut, BalanceTopup
from app.services.user_service import update_balance

router = APIRouter(prefix="/balance", tags=["balance"])


@router.post("/topup", response_model=BalanceOut)
async def topup(
    data: BalanceTopup,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if data.amount <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Amount must be positive")
    user = await update_balance(db, current_user, data.amount)
    return BalanceOut(balance=float(user.balance))


@router.get("", response_model=BalanceOut)
async def get_balance(current_user: Annotated[User, Depends(get_current_user)]):
    return BalanceOut(balance=float(current_user.balance))
