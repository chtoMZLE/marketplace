from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service import Service, ServiceStatus
from app.schemas.service import ServiceCreate, ServiceUpdate


async def create_service(db: AsyncSession, data: ServiceCreate, executor_id: str) -> Service:
    svc = Service(title=data.title, description=data.description, price=data.price, executor_id=executor_id)
    db.add(svc)
    await db.commit()
    await db.refresh(svc)
    return svc


async def get_services(db: AsyncSession, price_min: float | None, price_max: float | None) -> list[Service]:
    q = select(Service).where(Service.status == ServiceStatus.active)
    if price_min is not None:
        q = q.where(Service.price >= price_min)
    if price_max is not None:
        q = q.where(Service.price <= price_max)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_service(db: AsyncSession, service_id: str) -> Service | None:
    result = await db.execute(select(Service).where(Service.id == service_id))
    return result.scalar_one_or_none()


async def update_service(db: AsyncSession, svc: Service, data: ServiceUpdate) -> Service:
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(svc, field, val)
    await db.commit()
    await db.refresh(svc)
    return svc
