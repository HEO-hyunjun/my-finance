from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.dashboard import AIInsightsResponse
from app.services.dashboard_service import get_dashboard_summary
from app.services.insight_service import get_ai_insights

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


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
