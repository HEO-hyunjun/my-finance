from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.calendar import CalendarEventsResponse
from app.services.calendar_service import get_calendar_events

router = APIRouter(tags=["Calendar"])


@router.get("/events", response_model=CalendarEventsResponse)
async def get_events(
    year: int = Query(..., ge=2020, le=2100, description="조회 연도"),
    month: int = Query(..., ge=1, le=12, description="조회 월"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """월별 캘린더 이벤트 조회"""
    return await get_calendar_events(
        db=db,
        user_id=current_user.id,
        year=year,
        month=month,
    )
