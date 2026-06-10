from pydantic import BaseModel, Field, field_validator

from app.models.service import ServiceStatus


class ServiceCreate(BaseModel):
    title: str = Field(..., description="Название услуги", examples=["Разработка лендинга"])
    description: str = Field(..., description="Подробное описание услуги", examples=["Создам лендинг под ключ за 3 дня"])
    price: float = Field(..., gt=0, description="Стоимость в рублях", examples=[5000.0])

    @field_validator("price")
    @classmethod
    def price_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Price must be positive")
        return v


class ServiceUpdate(BaseModel):
    title: str | None = Field(None, description="Новое название")
    description: str | None = Field(None, description="Новое описание")
    price: float | None = Field(None, gt=0, description="Новая цена")
    status: ServiceStatus | None = Field(None, description="Новый статус")


class ServiceOut(BaseModel):
    id: str = Field(..., description="UUID услуги")
    title: str = Field(..., description="Название услуги")
    description: str = Field(..., description="Описание услуги")
    price: float = Field(..., description="Стоимость в рублях")
    executor_id: str = Field(..., description="UUID исполнителя")
    status: ServiceStatus = Field(..., description="Статус услуги")

    model_config = {"from_attributes": True}
