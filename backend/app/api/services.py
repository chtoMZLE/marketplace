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


@router.post("", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
async def create(
    data: ServiceCreate,
    current_user: Annotated[User, Depends(require_role(UserRole.executor))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_service(db, data, current_user.id)


@router.get("", response_model=list[ServiceOut])
async def list_services(
    price_min: float | None = Query(None),
    price_max: float | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_services(db, price_min, price_max)


@router.get("/{service_id}", response_model=ServiceOut)
async def get_one(service_id: str, db: AsyncSession = Depends(get_db)):
    svc = await get_service(db, service_id)
    if not svc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return svc


@router.put("/{service_id}", response_model=ServiceOut)
async def update(
    service_id: str,
    data: ServiceUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = await get_service(db, service_id)
    if not svc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    if svc.executor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the owner")
    return await update_service(db, svc, data)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    service_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = await get_service(db, service_id)
    if not svc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    if svc.executor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the owner")
    await update_service(db, svc, ServiceUpdate(status=ServiceStatus.deleted))
