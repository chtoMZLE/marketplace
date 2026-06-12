from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from jwt.exceptions import InvalidTokenError as JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.rate_limit import rate_limit
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.models.user import User
from app.schemas.user import RefreshRequest, TokenPair, UserLogin, UserOut, UserRegister
from app.services.user_service import create_user, get_user_by_email

router = APIRouter(tags=["auth"])

_401 = {401: {"description": "Неверные учётные данные"}}
_409 = {409: {"description": "Email уже зарегистрирован"}}


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description="Создаёт аккаунт с ролью `customer` или `executor`. Email должен быть уникальным.",
    responses={**_409, 422: {"description": "Ошибка валидации (слабый пароль, неверный email)"},
               429: {"description": "Слишком много запросов"}},
    dependencies=[Depends(rate_limit)],
)
async def register(data: UserRegister, db: Annotated[AsyncSession, Depends(get_db)]):
    existing = await get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email уже зарегистрирован")
    user = await create_user(db, data.email, data.password, data.role)
    return user


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Вход и получение JWT-токенов",
    description="Возвращает пару токенов: `access_token` (30 мин) и `refresh_token` (7 дней).",
    responses={**_401, 429: {"description": "Слишком много запросов"}},
    dependencies=[Depends(rate_limit)],
)
async def login(data: UserLogin, db: Annotated[AsyncSession, Depends(get_db)]):
    user = await get_user_by_email(db, data.email)
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post(
    "/token/refresh",
    response_model=TokenPair,
    summary="Обновление access-токена",
    description="Принимает `refresh_token` и возвращает новую пару токенов.",
    responses=_401,
)
async def refresh_token(data: RefreshRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        payload = decode_token(data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный тип токена")
        user_id: str = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный refresh-токен") from None

    return TokenPair(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.get(
    "/me",
    response_model=UserOut,
    summary="Профиль текущего пользователя",
    description="Возвращает данные авторизованного пользователя: id, email, роль, баланс.",
    responses=_401,
)
async def me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user
