from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.balance import router as balance_router
from app.api.orders import router as orders_router
from app.api.services import router as services_router

app = FastAPI(title="Marketplace API", version="1.0.0")

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


@app.get("/health")
async def health():
    return {"status": "ok"}
