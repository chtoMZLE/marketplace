from pydantic import BaseModel

from app.models.order import OrderStatus


class OrderCreate(BaseModel):
    service_id: str


class OrderOut(BaseModel):
    id: str
    service_id: str
    customer_id: str
    status: OrderStatus
    escrow_tx_id: str | None

    model_config = {"from_attributes": True}


class BalanceTopup(BaseModel):
    amount: float


class BalanceOut(BaseModel):
    balance: float
