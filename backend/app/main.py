from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.redis import close_redis

# Auth & Users
from app.api.v1.endpoints import auth as auth_router
from app.api.v1.endpoints import users as users_router

# New v2 core
from app.api.v1.endpoints import accounts as accounts_router
from app.api.v1.endpoints import entries as entries_router
from app.api.v1.endpoints import categories as categories_router
from app.api.v1.endpoints import schedules as schedules_router

# Existing features (to be updated in Phase 2)
from app.api.v1.endpoints import budget as budget_router
from app.api.v1.endpoints import calendar as calendar_router
from app.api.v1.endpoints import carryover as carryover_router
from app.api.v1.endpoints import dashboard as dashboard_router
from app.api.v1.endpoints import market as market_router
from app.api.v1.endpoints import portfolio as portfolio_router
from app.api.v1.endpoints import securities as securities_router
from app.api.v1.endpoints import settings as settings_router
from app.api.v1.endpoints import chatbot as chatbot_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 다운타임 중 누락된 일일 태스크 보상 실행
    try:
        from app.tasks.startup_tasks import run_missed_tasks
        run_missed_tasks()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Startup compensation tasks failed: {e}")

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

# Auth & Users
app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users_router.router, prefix="/api/v1/users", tags=["users"])

# New v2 core
app.include_router(accounts_router.router, prefix="/api/v1/accounts", tags=["accounts"])
app.include_router(entries_router.router, prefix="/api/v1/entries", tags=["entries"])
app.include_router(categories_router.router, prefix="/api/v1/categories", tags=["categories"])
app.include_router(schedules_router.router, prefix="/api/v1/schedules", tags=["schedules"])

# Existing features (to be updated in Phase 2)
app.include_router(budget_router.router, prefix="/api/v1/budget", tags=["budget"])
app.include_router(calendar_router.router, prefix="/api/v1/calendar", tags=["calendar"])
app.include_router(carryover_router.router, prefix="/api/v1/budget/carryover", tags=["carryover"])
app.include_router(dashboard_router.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(market_router.router, prefix="/api/v1/market", tags=["market"])
app.include_router(securities_router.router, prefix="/api/v1/securities", tags=["securities"])
app.include_router(portfolio_router.router, prefix="/api/v1/portfolio", tags=["portfolio"])
app.include_router(settings_router.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(chatbot_router.router, prefix="/api/v1/chatbot", tags=["chatbot"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
