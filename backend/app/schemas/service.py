from pydantic import BaseModel, field_validator

from app.models.service import ServiceStatus


class ServiceCreate(BaseModel):
    title: str
    description: str
    price: float

    @field_validator("price")
    @classmethod
    def price_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Price must be positive")
        return v


class ServiceUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price: float | None = None
    status: ServiceStatus | None = None


class ServiceOut(BaseModel):
    id: str
    title: str
    description: str
    price: float
    executor_id: str
    status: ServiceStatus

    model_config = {"from_attributes": True}
