from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.carryover import (
    CarryoverSettingCreate, CarryoverSettingResponse,
    CarryoverLogResponse, CarryoverExecuteRequest, CarryoverPreviewResponse,
)
from app.services import carryover_service
from app.models.carryover import CarryoverSetting
from sqlalchemy import select
import uuid

router = APIRouter(tags=["budget-carryover"])


@router.get("/settings", response_model=list[CarryoverSettingResponse])
async def list_settings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await carryover_service.get_carryover_settings(db, user.id)


@router.delete("/settings/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_setting(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(CarryoverSetting).where(
        CarryoverSetting.user_id == user.id,
        CarryoverSetting.category_id == category_id,
    )
    setting = (await db.execute(stmt)).scalar_one_or_none()
    if setting:
        await db.delete(setting)
        await db.commit()


@router.post("/settings", response_model=CarryoverSettingResponse, status_code=status.HTTP_201_CREATED)
async def upsert_setting(
    data: CarryoverSettingCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await carryover_service.upsert_carryover_setting(db, user.id, data)


@router.get("/preview", response_model=list[CarryoverPreviewResponse])
async def preview_carryover(
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await carryover_service.get_carryover_preview(db, user.id, period_start, period_end)


@router.post("/execute", response_model=list[CarryoverLogResponse])
async def execute_carryover(
    data: CarryoverExecuteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await carryover_service.execute_carryover(db, user.id, data.period_start, data.period_end)


@router.get("/logs", response_model=list[CarryoverLogResponse])
async def list_logs(
    period_start: date | None = None,
    period_end: date | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await carryover_service.get_carryover_logs(db, user.id, period_start, period_end)
