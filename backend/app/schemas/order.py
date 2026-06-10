from pydantic import BaseModel, Field

from app.models.order import OrderStatus


class OrderCreate(BaseModel):
    service_id: str = Field(..., description="UUID услуги, которую нужно заказать")


class OrderOut(BaseModel):
    id: str = Field(..., description="UUID заказа")
    service_id: str = Field(..., description="UUID заказанной услуги")
    customer_id: str = Field(..., description="UUID покупателя")
    status: OrderStatus = Field(..., description="Текущий статус заказа")
    escrow_tx_id: str | None = Field(None, description="UUID эскроу-счёта в платёжном микросервисе")

    model_config = {"from_attributes": True}


class BalanceTopup(BaseModel):
    amount: float = Field(..., gt=0, description="Сумма пополнения в рублях", examples=[500.0])


class BalanceOut(BaseModel):
    balance: float = Field(..., description="Актуальный баланс в рублях", examples=[1500.0])
