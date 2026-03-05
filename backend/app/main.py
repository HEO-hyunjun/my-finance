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
    # 서버 시작 시 뉴스 캐시 워밍 (DB → Redis)
    try:
        from app.core.redis import get_redis
        from app.services.news_service import NewsService

        redis_client = await get_redis()
        news_service = NewsService(redis_client)
        warmed = await news_service.warm_cache_from_db()
        if warmed:
            import logging
            logging.getLogger(__name__).info(f"News cache warmed with {warmed} articles")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"News cache warming failed: {e}")

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
