from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus


async def create_order(db: AsyncSession, service_id: str, customer_id: str, escrow_id: str) -> Order:
    order = Order(service_id=service_id, customer_id=customer_id, escrow_tx_id=escrow_id)
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


async def get_order(db: AsyncSession, order_id: str) -> Order | None:
    result = await db.execute(select(Order).where(Order.id == order_id))
    return result.scalar_one_or_none()


async def get_orders_for_user(db: AsyncSession, user_id: str) -> list[Order]:
    result = await db.execute(
        select(Order).where((Order.customer_id == user_id))
    )
    return list(result.scalars().all())


async def set_status(db: AsyncSession, order: Order, status: OrderStatus) -> Order:
    order.status = status
    await db.commit()
    await db.refresh(order)
    return order
