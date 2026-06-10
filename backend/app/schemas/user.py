from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserRegister(BaseModel):
    email: EmailStr = Field(..., description="Email-адрес пользователя", examples=["user@example.com"])
    password: str = Field(..., description="Пароль (минимум 8 символов)", examples=["secret123"])
    role: UserRole = Field(..., description="Роль: `customer` — покупатель, `executor` — исполнитель")

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Пароль должен содержать не менее 8 символов")
        return v


class UserLogin(BaseModel):
    email: EmailStr = Field(..., examples=["user@example.com"])
    password: str = Field(..., examples=["secret123"])


class TokenPair(BaseModel):
    access_token: str = Field(..., description="JWT access-токен (срок действия 30 мин)")
    refresh_token: str = Field(..., description="JWT refresh-токен (срок действия 7 дней)")
    token_type: str = Field(default="bearer", description="Тип токена")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Действующий refresh-токен")


class UserOut(BaseModel):
    id: str = Field(..., description="UUID пользователя")
    email: str = Field(..., description="Email пользователя")
    role: UserRole = Field(..., description="Роль пользователя")
    balance: float = Field(..., description="Текущий баланс в рублях", examples=[1000.0])

    model_config = {"from_attributes": True}
