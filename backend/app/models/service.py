import enum
import uuid

from sqlalchemy import DECIMAL, TIMESTAMP, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ServiceStatus(enum.StrEnum):
    active = "active"
    paused = "paused"
    deleted = "deleted"


class Service(Base):
    __tablename__ = "services"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    executor_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    status: Mapped[ServiceStatus] = mapped_column(Enum(ServiceStatus), nullable=False, default=ServiceStatus.active)
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    executor = relationship("User", foreign_keys=[executor_id])
