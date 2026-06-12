from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.service import ServiceStatus
from app.models.user import User, UserRole
from app.schemas.service import ServiceCreate, ServiceOut, ServiceUpdate
from app.services.service_service import create_service, get_service, get_services, update_service

router = APIRouter(prefix="/services", tags=["services"])

_401 = {401: {"description": "Не авторизован"}}
_403 = {403: {"description": "Недостаточно прав"}}
_404 = {404: {"description": "Услуга не найдена"}}


@router.post(
    "",
    response_model=ServiceOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создать услугу",
    description="Доступно только для исполнителей (`executor`). Услуга сразу становится активной.",
    responses={**_401, **_403},
)
async def create(
    data: ServiceCreate,
    current_user: Annotated[User, Depends(require_role(UserRole.executor))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_service(db, data, current_user.id)


@router.get(
    "",
    response_model=list[ServiceOut],
    summary="Список услуг",
    description="Возвращает все активные услуги. Поддерживает фильтрацию по цене.",
)
async def list_services(
    db: Annotated[AsyncSession, Depends(get_db)],
    price_min: Annotated[float | None, Query(description="Минимальная цена", ge=0)] = None,
    price_max: Annotated[float | None, Query(description="Максимальная цена", ge=0)] = None,
):
    return await get_services(db, price_min, price_max)


@router.get(
    "/{service_id}",
    response_model=ServiceOut,
    summary="Получить услугу по ID",
    responses=_404,
)
async def get_one(service_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    svc = await get_service(db, service_id)
    if not svc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Услуга не найдена")
    return svc


@router.put(
    "/{service_id}",
    response_model=ServiceOut,
    summary="Обновить услугу",
    description="Редактировать может только владелец услуги.",
    responses={**_401, **_403, **_404},
)
async def update(
    service_id: str,
    data: ServiceUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = await get_service(db, service_id)
    if not svc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Услуга не найдена")
    if svc.executor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь владельцем услуги")
    return await update_service(db, svc, data)


@router.delete(
    "/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить услугу",
    description="Мягкое удаление: статус услуги меняется на `deleted`. Только для владельца.",
    responses={**_401, **_403, **_404},
)
async def delete(
    service_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = await get_service(db, service_id)
    if not svc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Услуга не найдена")
    if svc.executor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь владельцем услуги")
    await update_service(db, svc, ServiceUpdate(status=ServiceStatus.deleted))
