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

router = APIRouter(prefix="/budget/carryover", tags=["budget-carryover"])


@router.get("/settings", response_model=list[CarryoverSettingResponse])
async def list_settings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await carryover_service.get_carryover_settings(db, user.id)


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
