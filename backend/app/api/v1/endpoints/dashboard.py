from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.dashboard import AIInsightsResponse, DashboardSummaryResponse
from app.services.dashboard_service import get_dashboard_summary
from app.services.insight_service import get_ai_insights
from app.services.market_service import MarketService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis = await get_redis()
    market = MarketService(redis)
    return await get_dashboard_summary(
        db=db,
        user_id=current_user.id,
        market=market,
        redis=redis,
        salary_day=current_user.salary_day,
    )


@router.get("/insights", response_model=AIInsightsResponse)
async def dashboard_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI 기반 재무 인사이트 조회"""
    redis = await get_redis()
    market = MarketService(redis)
    insights = await get_ai_insights(
        db=db,
        user_id=current_user.id,
        market=market,
        redis_client=redis,
    )
    return AIInsightsResponse(insights=insights)
