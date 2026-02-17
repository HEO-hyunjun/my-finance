import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# --- Asset Snapshot ---

class AssetSnapshotResponse(BaseModel):
    id: uuid.UUID
    snapshot_date: date
    total_krw: float
    breakdown: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class AssetTimelineResponse(BaseModel):
    snapshots: list[AssetSnapshotResponse]
    period: str
    start_date: date
    end_date: date


# --- Goal Asset ---

class GoalAssetCreate(BaseModel):
    target_amount: Decimal = Field(gt=0)
    target_date: date | None = None


class GoalAssetUpdate(BaseModel):
    target_amount: Decimal | None = Field(default=None, gt=0)
    target_date: date | None = None


class GoalAssetResponse(BaseModel):
    id: uuid.UUID
    target_amount: float
    target_date: date | None
    current_amount: float
    achievement_rate: float
    remaining_amount: float
    monthly_required: float | None
    estimated_date: date | None
    created_at: datetime
    updated_at: datetime


# --- Portfolio Target ---

class PortfolioTargetCreate(BaseModel):
    asset_type: str
    target_ratio: Decimal = Field(ge=0, le=1)


class PortfolioTargetBulkCreate(BaseModel):
    targets: list[PortfolioTargetCreate]


class PortfolioTargetResponse(BaseModel):
    id: uuid.UUID
    asset_type: str
    target_ratio: float
    current_ratio: float
    deviation: float
    created_at: datetime
    updated_at: datetime


class RebalancingAnalysisResponse(BaseModel):
    targets: list[PortfolioTargetResponse]
    total_deviation: float
    needs_rebalancing: bool
    threshold: float
    suggestions: list[dict]


# --- Rebalancing Alert ---

class RebalancingAlertResponse(BaseModel):
    id: uuid.UUID
    snapshot_date: date
    deviations: dict
    suggestion: dict
    threshold: float
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
