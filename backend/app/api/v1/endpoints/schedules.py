import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.recurring_schedule import (
    ScheduleCreate,
    ScheduleResponse,
    ScheduleUpdate,
)
from app.services import schedule_service

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await schedule_service.get_schedules(db, current_user.id)


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
