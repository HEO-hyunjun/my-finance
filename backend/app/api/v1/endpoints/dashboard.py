from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.dashboard import AIInsightsResponse
from app.services.dashboard_service import get_dashboard_summary
from app.services.insight_service import generate_daily_insights, get_ai_insights
from app.services.market_service import MarketService

router = APIRouter(tags=["Dashboard"])


@router.get("/summary")
async def dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_dashboard_summary(db=db, user_id=current_user.id)


@router.get("/insights", response_model=AIInsightsResponse)
async def dashboard_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI 기반 재무 인사이트 조회 (DB에서 오늘 날짜 데이터 반환)"""
    insights = await get_ai_insights(db=db, user_id=current_user.id)
    return AIInsightsResponse(insights=insights)


@router.post("/insights/generate", response_model=AIInsightsResponse)
async def generate_dashboard_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """오늘자 AI 인사이트를 동기 생성 (이미 있으면 재생성). LLM 실패 시 502."""
    market = MarketService(redis)
    try:
        await generate_daily_insights(
            db=db, user_id=current_user.id, market=market, raise_on_error=True,
        )
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"LLM 호출 실패: {type(e).__name__}: {e}",
        )
    insights = await get_ai_insights(db=db, user_id=current_user.id)
    return AIInsightsResponse(insights=insights)
