import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import AssetSnapshot, PortfolioTarget, RebalancingAlert, GoalAsset
from app.schemas.portfolio import (
    AssetSnapshotResponse, AssetTimelineResponse,
    GoalAssetCreate, GoalAssetResponse,
    PortfolioTargetBulkCreate, PortfolioTargetResponse,
    RebalancingAnalysisResponse, RebalancingAlertResponse,
)


# --- Asset Snapshots ---

async def create_snapshot(
    db: AsyncSession, user_id: uuid.UUID, total_krw: Decimal, breakdown: dict
) -> AssetSnapshotResponse:
    today = date.today()
    # Upsert: update if exists for today
    result = await db.execute(
        select(AssetSnapshot).where(
            AssetSnapshot.user_id == user_id,
            AssetSnapshot.snapshot_date == today,
        )
    )
    snapshot = result.scalar_one_or_none()

    if snapshot:
        snapshot.total_krw = total_krw
        snapshot.breakdown = breakdown
    else:
        snapshot = AssetSnapshot(
            user_id=user_id,
            snapshot_date=today,
            total_krw=total_krw,
            breakdown=breakdown,
        )
        db.add(snapshot)

    await db.commit()
    await db.refresh(snapshot)
    return AssetSnapshotResponse.model_validate(snapshot)


async def get_asset_timeline(
    db: AsyncSession, user_id: uuid.UUID, period: str = "1M"
) -> AssetTimelineResponse:
    today = date.today()
    period_map = {
        "1W": timedelta(weeks=1),
        "1M": timedelta(days=30),
        "3M": timedelta(days=90),
        "6M": timedelta(days=180),
        "1Y": timedelta(days=365),
        "ALL": timedelta(days=3650),
    }
    delta = period_map.get(period, timedelta(days=30))
    start_date = today - delta

    result = await db.execute(
        select(AssetSnapshot)
        .where(
            AssetSnapshot.user_id == user_id,
            AssetSnapshot.snapshot_date >= start_date,
        )
        .order_by(AssetSnapshot.snapshot_date.asc())
    )
    snapshots = result.scalars().all()

    return AssetTimelineResponse(
        snapshots=[AssetSnapshotResponse.model_validate(s) for s in snapshots],
        period=period,
        start_date=start_date,
        end_date=today,
    )


# --- Goal Asset ---

async def get_goal(
    db: AsyncSession, user_id: uuid.UUID, current_amount: float
) -> GoalAssetResponse | None:
    result = await db.execute(
        select(GoalAsset).where(GoalAsset.user_id == user_id)
    )
    goal = result.scalar_one_or_none()
    if not goal:
        return None

    target = float(goal.target_amount)
    achievement = (current_amount / target * 100) if target > 0 else 0
    remaining = max(0, target - current_amount)

    # Estimate monthly required and date
    monthly_required = None
    estimated_date = None
    if goal.target_date and remaining > 0:
        months_left = max(1, (goal.target_date - date.today()).days / 30)
        monthly_required = remaining / months_left

    # Simple trend estimation from snapshots
    if remaining > 0:
        snap_result = await db.execute(
            select(AssetSnapshot)
            .where(AssetSnapshot.user_id == user_id)
            .order_by(AssetSnapshot.snapshot_date.desc())
            .limit(60)
        )
        snaps = snap_result.scalars().all()
        if len(snaps) >= 2:
            oldest = snaps[-1]
            newest = snaps[0]
            days_diff = (newest.snapshot_date - oldest.snapshot_date).days
            if days_diff > 0:
                daily_growth = (float(newest.total_krw) - float(oldest.total_krw)) / days_diff
                if daily_growth > 0:
                    days_needed = int(remaining / daily_growth)
                    estimated_date = date.today() + timedelta(days=days_needed)

    return GoalAssetResponse(
        id=goal.id,
        target_amount=target,
        target_date=goal.target_date,
        current_amount=current_amount,
        achievement_rate=round(achievement, 1),
        remaining_amount=remaining,
        monthly_required=round(monthly_required, 0) if monthly_required else None,
        estimated_date=estimated_date,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


async def upsert_goal(
    db: AsyncSession, user_id: uuid.UUID, data: GoalAssetCreate
) -> GoalAssetResponse:
    result = await db.execute(
        select(GoalAsset).where(GoalAsset.user_id == user_id)
    )
    goal = result.scalar_one_or_none()

    if goal:
        goal.target_amount = data.target_amount
        goal.target_date = data.target_date
    else:
        goal = GoalAsset(
            user_id=user_id,
            target_amount=data.target_amount,
            target_date=data.target_date,
        )
        db.add(goal)

    await db.commit()
    await db.refresh(goal)

    return GoalAssetResponse(
        id=goal.id,
        target_amount=float(goal.target_amount),
        target_date=goal.target_date,
        current_amount=0,
        achievement_rate=0,
        remaining_amount=float(goal.target_amount),
        monthly_required=None,
        estimated_date=None,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


# --- Portfolio Targets ---

async def get_portfolio_targets(
    db: AsyncSession, user_id: uuid.UUID, breakdown: dict
) -> list[PortfolioTargetResponse]:
    result = await db.execute(
        select(PortfolioTarget)
        .where(PortfolioTarget.user_id == user_id)
        .order_by(PortfolioTarget.asset_type)
    )
    targets = result.scalars().all()

    total_value = sum(breakdown.values()) if breakdown else 1

    return [
        PortfolioTargetResponse(
            id=t.id,
            asset_type=t.asset_type,
            target_ratio=float(t.target_ratio),
            current_ratio=round(breakdown.get(t.asset_type, 0) / total_value, 4) if total_value > 0 else 0,
            deviation=round(
                breakdown.get(t.asset_type, 0) / total_value - float(t.target_ratio), 4
            ) if total_value > 0 else 0,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in targets
    ]


async def set_portfolio_targets(
    db: AsyncSession, user_id: uuid.UUID, data: PortfolioTargetBulkCreate
) -> list[PortfolioTargetResponse]:
    # Validate sum = 1.0
    total = sum(float(t.target_ratio) for t in data.targets)
    if abs(total - 1.0) > 0.01:
        raise ValueError(f"Target ratios must sum to 1.0, got {total}")

    # Delete existing
    existing = await db.execute(
        select(PortfolioTarget).where(PortfolioTarget.user_id == user_id)
    )
    for t in existing.scalars().all():
        await db.delete(t)

    # Create new
    new_targets = []
    for item in data.targets:
        target = PortfolioTarget(
            user_id=user_id,
            asset_type=item.asset_type,
            target_ratio=item.target_ratio,
        )
        db.add(target)
        new_targets.append(target)

    await db.commit()
    for t in new_targets:
        await db.refresh(t)

    return [
        PortfolioTargetResponse(
            id=t.id,
            asset_type=t.asset_type,
            target_ratio=float(t.target_ratio),
            current_ratio=0,
            deviation=0,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in new_targets
    ]


async def get_rebalancing_analysis(
    db: AsyncSession, user_id: uuid.UUID, breakdown: dict, threshold: float = 0.05
) -> RebalancingAnalysisResponse:
    targets = await get_portfolio_targets(db, user_id, breakdown)
    total_value = sum(breakdown.values()) if breakdown else 0

    total_deviation = sum(abs(t.deviation) for t in targets)
    needs_rebalancing = any(abs(t.deviation) >= threshold for t in targets)

    suggestions = []
    if needs_rebalancing and total_value > 0:
        for t in targets:
            if abs(t.deviation) >= threshold:
                adjust_amount = t.deviation * total_value
                suggestions.append({
                    "asset_type": t.asset_type,
                    "action": "sell" if t.deviation > 0 else "buy",
                    "amount_krw": round(abs(adjust_amount)),
                    "deviation": round(t.deviation * 100, 1),
                })

    return RebalancingAnalysisResponse(
        targets=targets,
        total_deviation=round(total_deviation, 4),
        needs_rebalancing=needs_rebalancing,
        threshold=threshold,
        suggestions=suggestions,
    )


async def get_rebalancing_alerts(
    db: AsyncSession, user_id: uuid.UUID, unread_only: bool = False
) -> list[RebalancingAlertResponse]:
    query = select(RebalancingAlert).where(RebalancingAlert.user_id == user_id)
    if unread_only:
        query = query.where(RebalancingAlert.is_read.is_(False))
    query = query.order_by(RebalancingAlert.created_at.desc()).limit(20)

    result = await db.execute(query)
    alerts = result.scalars().all()
    return [RebalancingAlertResponse.model_validate(a) for a in alerts]


async def mark_alert_read(
    db: AsyncSession, user_id: uuid.UUID, alert_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(RebalancingAlert).where(
            RebalancingAlert.id == alert_id,
            RebalancingAlert.user_id == user_id,
        )
    )
    alert = result.scalar_one_or_none()
    if alert:
        alert.is_read = True
        await db.commit()
