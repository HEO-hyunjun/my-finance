import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.asset import AssetCreate, AssetResponse, AssetHoldingResponse, AssetSummaryResponse
from app.services import asset_service
from app.services.market_service import MarketService

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[AssetResponse])
async def list_assets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await asset_service.get_assets(db, current_user.id)


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    data: AssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await asset_service.create_asset(db, current_user.id, data)


@router.get("/summary", response_model=AssetSummaryResponse)
async def get_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
):
    market = MarketService(redis)
    return await asset_service.get_asset_summary(db, current_user.id, market)


@router.get("/{asset_id}", response_model=AssetHoldingResponse)
async def get_asset_detail(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
):
    market = MarketService(redis)
    return await asset_service.get_asset_detail(db, current_user.id, asset_id, market)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await asset_service.delete_asset(db, current_user.id, asset_id)
