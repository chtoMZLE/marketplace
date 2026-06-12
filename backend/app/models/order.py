import enum
import uuid

from sqlalchemy import TIMESTAMP, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OrderStatus(enum.StrEnum):
    pending = "pending"
    active = "active"
    completed = "completed"
    disputed = "disputed"
    cancelled = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    service_id: Mapped[str] = mapped_column(String(36), ForeignKey("services.id"), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), nullable=False, default=OrderStatus.pending)
    escrow_tx_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    service = relationship("Service", foreign_keys=[service_id])
    customer = relationship("User", foreign_keys=[customer_id])
