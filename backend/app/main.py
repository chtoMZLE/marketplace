from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.balance import router as balance_router
from app.api.orders import router as orders_router
from app.api.services import router as services_router
from app.core.config import settings
from app.services import payment_client as pc

_DESCRIPTION = """
Marketplace API — платформа для заказа и оказания услуг с эскроу-расчётами.

## Авторизация
Большинство эндпоинтов требуют JWT Bearer-токен.
Получите `access_token` через `/login` и нажмите **Authorize** вверху страницы.

## Роли
| Роль | Возможности |
|------|-------------|
| `customer` | Пополнение баланса, создание и отмена заказов, открытие споров, подтверждение выполнения |
| `executor` | Создание услуг, принятие заказов в работу |

## Жизненный цикл заказа
```
pending ──► cancelled   (покупатель отменяет до принятия)
   │
   ▼
active  ──► completed   (покупатель подтверждает выполнение)
   │
   └──────► disputed    (любая сторона открывает спор)

pending также может перейти в disputed напрямую
```
"""

_TAGS = [
    {
        "name": "auth",
        "description": "Регистрация, вход, обновление JWT-токенов, профиль текущего пользователя.",
    },
    {
        "name": "services",
        "description": "CRUD услуг. Создавать и редактировать могут только исполнители (`executor`).",
    },
    {
        "name": "orders",
        "description": (
            "Управление заказами. Средства блокируются в эскроу при создании заказа "
            "и освобождаются исполнителю при подтверждении или возвращаются покупателю при отмене."
        ),
    },
    {
        "name": "balance",
        "description": "Пополнение и просмотр баланса покупателя. Баланс синхронизируется с платёжным микросервисом.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    pc._client = httpx.AsyncClient(base_url=settings.payment_service_url, timeout=10)
    yield
    await pc._client.aclose()
    pc._client = None


app = FastAPI(
    title="Marketplace API",
    version="1.0.0",
    description=_DESCRIPTION,
    contact={"name": "Marketplace"},
    openapi_tags=_TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(services_router)
app.include_router(orders_router)
app.include_router(balance_router)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}
