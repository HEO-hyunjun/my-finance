from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.redis import close_redis
from app.api.v1.endpoints import (
    assets, transactions, market, budget, expenses, fixed_expenses,
    installments, dashboard, news, calendar, chatbot, users,
    incomes, carryover, portfolio, auth, transfers,
)
from app.api.v1.endpoints import settings as settings_endpoints


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API v1 라우터 등록
app.include_router(auth.router, prefix="/api/v1")
app.include_router(assets.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(market.router, prefix="/api/v1")
app.include_router(budget.router, prefix="/api/v1")
app.include_router(expenses.router, prefix="/api/v1")
app.include_router(fixed_expenses.router, prefix="/api/v1")
app.include_router(installments.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(news.router, prefix="/api/v1")
app.include_router(calendar.router, prefix="/api/v1")
app.include_router(chatbot.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(incomes.router, prefix="/api/v1")
app.include_router(carryover.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(transfers.router, prefix="/api/v1")
app.include_router(settings_endpoints.router, prefix="/api/v1")


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
