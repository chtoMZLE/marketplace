import enum
import uuid

from sqlalchemy import DECIMAL, TIMESTAMP, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserRole(enum.StrEnum):
    customer = "customer"
    executor = "executor"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    balance: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False, default=0.0)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
