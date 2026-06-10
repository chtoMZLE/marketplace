import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/marketplace"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7
    payment_service_url: str = "http://localhost:8001"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def _warn_weak_secret(self) -> "Settings":
        weak = len(self.jwt_secret) < 32 or "change-me" in self.jwt_secret.lower()
        if weak:
            logger.warning(
                "JWT_SECRET is weak or default. "
                "Set a strong random secret for production: openssl rand -hex 32"
            )
        return self


settings = Settings()
