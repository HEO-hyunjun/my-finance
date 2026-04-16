import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.tz import today as tz_today
from app.models.entry import Entry
from app.models.user import User
from app.schemas.recurring_schedule import (
    ScheduleCreate,
    ScheduleResponse,
    ScheduleUpdate,
)
from app.services import schedule_service

router = APIRouter(tags=["schedules"])


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedules = await schedule_service.get_schedules(db, current_user.id)

    today = tz_today()
    executed_stmt = (
        select(Entry.recurring_schedule_id)
        .where(
            Entry.user_id == current_user.id,
            Entry.recurring_schedule_id.is_not(None),
            extract("year", Entry.transacted_at) == today.year,
            extract("month", Entry.transacted_at) == today.month,
        )
        .distinct()
    )
    executed_ids = set((await db.execute(executed_stmt)).scalars().all())

    result = []
    for s in schedules:
        data = ScheduleResponse.model_validate(s).model_dump()
        data["executed_this_month"] = s.id in executed_ids
        result.append(data)
    return result


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    data: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await schedule_service.create_schedule(
        db, current_user.id, data.model_dump()
    )


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await schedule_service.get_schedule(db, current_user.id, schedule_id)


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: uuid.UUID,
    data: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await schedule_service.update_schedule(
        db, current_user.id, schedule_id, data.model_dump(exclude_unset=True)
    )


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await schedule_service.delete_schedule(db, current_user.id, schedule_id)


@router.post("/{schedule_id}/toggle", response_model=ScheduleResponse)
async def toggle_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await schedule_service.toggle_schedule(db, current_user.id, schedule_id)


@router.post("/{schedule_id}/execute")
async def execute_schedule_now(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """스케줄을 오늘 날짜로 즉시 실행 (선납 등 수동 실행용)."""
    return await schedule_service.execute_schedule_now(db, current_user.id, schedule_id)
