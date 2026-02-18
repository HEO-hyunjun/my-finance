import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.asset import Asset, AssetType, InterestType
from app.models.transaction import Transaction, TransactionType
from app.schemas.asset import (
    AssetCreate,
    AssetUpdate,
    AssetResponse,
    AssetHoldingResponse,
    AssetSummaryResponse,
)
from app.services.interest_service import (
    calculate_deposit_interest,
    calculate_savings_interest,
    calculate_parking_interest,
)
from app.services.market_service import MarketService

INTEREST_BASED_TYPES = {AssetType.DEPOSIT, AssetType.SAVINGS, AssetType.PARKING}


async def create_asset(
    db: AsyncSession, user_id: uuid.UUID, data: AssetCreate
) -> AssetResponse:
    # 동일 자산 중복 체크
    stmt = select(Asset).where(
        Asset.user_id == user_id,
        Asset.asset_type == data.asset_type,
        Asset.symbol == data.symbol,
        Asset.name == data.name,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        from fastapi import HTTPException

        raise HTTPException(status_code=409, detail="Asset already exists")

    asset = Asset(
        user_id=user_id,
        asset_type=data.asset_type,
        symbol=data.symbol,
        name=data.name,
        interest_rate=data.interest_rate,
        interest_type=InterestType(data.interest_type) if data.interest_type else None,
        principal=data.principal,
        monthly_amount=data.monthly_amount,
        start_date=data.start_date,
        maturity_date=data.maturity_date,
        tax_rate=data.tax_rate,
        bank_name=data.bank_name,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return AssetResponse.model_validate(asset)


async def get_assets(db: AsyncSession, user_id: uuid.UUID) -> list[AssetResponse]:
    stmt = select(Asset).where(Asset.user_id == user_id).order_by(Asset.created_at)
    result = await db.execute(stmt)
    assets = result.scalars().all()
    return [AssetResponse.model_validate(a) for a in assets]


async def get_asset_detail(
    db: AsyncSession,
    user_id: uuid.UUID,
    asset_id: uuid.UUID,
    market: MarketService,
) -> AssetHoldingResponse:
    stmt = (
        select(Asset)
        .options(selectinload(Asset.transactions))
        .where(Asset.id == asset_id, Asset.user_id == user_id)
    )
    asset = (await db.execute(stmt)).scalar_one_or_none()
    if not asset:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Asset not found")

    holding = await _calculate_holding(asset, market)
    return holding


async def get_asset_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    market: MarketService,
) -> AssetSummaryResponse:
    stmt = (
        select(Asset)
        .options(selectinload(Asset.transactions))
        .where(Asset.user_id == user_id)
    )
    result = await db.execute(stmt)
    assets = result.scalars().all()

    holdings: list[AssetHoldingResponse] = []
    breakdown: dict[str, float] = {}
    total_value = 0.0
    total_invested = 0.0

    for asset in assets:
        holding = await _calculate_holding(asset, market)
        holdings.append(holding)
        total_value += holding.total_value_krw
        total_invested += holding.total_invested_krw
        asset_type_key = asset.asset_type.value
        breakdown[asset_type_key] = breakdown.get(asset_type_key, 0) + holding.total_value_krw

    total_profit = total_value - total_invested
    total_rate = (total_profit / total_invested * 100) if total_invested > 0 else 0.0

    return AssetSummaryResponse(
        total_value_krw=round(total_value, 2),
        total_invested_krw=round(total_invested, 2),
        total_profit_loss=round(total_profit, 2),
        total_profit_loss_rate=round(total_rate, 2),
        breakdown={k: round(v, 2) for k, v in breakdown.items()},
        holdings=holdings,
    )


async def update_asset(
    db: AsyncSession, user_id: uuid.UUID, asset_id: uuid.UUID, data: AssetUpdate
) -> AssetResponse:
    stmt = select(Asset).where(Asset.id == asset_id, Asset.user_id == user_id)
    asset = (await db.execute(stmt)).scalar_one_or_none()
    if not asset:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Asset not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(asset, field, value)

    await db.commit()
    await db.refresh(asset)
    return AssetResponse.model_validate(asset)


async def delete_asset(
    db: AsyncSession, user_id: uuid.UUID, asset_id: uuid.UUID
) -> None:
    stmt = select(Asset).where(Asset.id == asset_id, Asset.user_id == user_id)
    asset = (await db.execute(stmt)).scalar_one_or_none()
    if not asset:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Asset not found")

    await db.delete(asset)
    await db.commit()


async def _calculate_holding(
    asset: Asset, market: MarketService
) -> AssetHoldingResponse:
    """보유량, 평균단가, 수익률 계산 (이자 기반 자산 포함)"""
    today = date.today()

    # --- 예금 ---
    if asset.asset_type == AssetType.DEPOSIT:
        result = calculate_deposit_interest(
            principal=asset.principal,
            annual_rate=asset.interest_rate,
            start_date=asset.start_date,
            as_of_date=today,
            maturity_date=asset.maturity_date,
            interest_type=asset.interest_type.value if asset.interest_type else "simple",
            tax_rate=asset.tax_rate or Decimal("15.4"),
        )
        p = float(asset.principal)
        return AssetHoldingResponse(
            id=asset.id,
            asset_type=asset.asset_type,
            symbol=None,
            name=asset.name,
            quantity=1,
            avg_price=p,
            current_price=p,
            exchange_rate=None,
            total_value_krw=result["total_value_krw"],
            total_invested_krw=p,
            profit_loss=result["accrued_interest_aftertax"],
            profit_loss_rate=round(result["accrued_interest_aftertax"] / p * 100, 2) if p else 0,
            created_at=asset.created_at,
            interest_rate=float(asset.interest_rate),
            interest_type=asset.interest_type.value if asset.interest_type else "simple",
            bank_name=asset.bank_name,
            principal=p,
            start_date=asset.start_date,
            maturity_date=asset.maturity_date,
            tax_rate=float(asset.tax_rate) if asset.tax_rate else 15.4,
            accrued_interest_pretax=result["accrued_interest_pretax"],
            accrued_interest_aftertax=result["accrued_interest_aftertax"],
            maturity_amount=result["maturity_amount"],
            elapsed_months=result["elapsed_months"],
            total_months=result["total_months"],
        )

    # --- 적금 ---
    if asset.asset_type == AssetType.SAVINGS:
        result = calculate_savings_interest(
            monthly_amount=asset.monthly_amount,
            annual_rate=asset.interest_rate,
            start_date=asset.start_date,
            as_of_date=today,
            maturity_date=asset.maturity_date,
            tax_rate=asset.tax_rate or Decimal("15.4"),
            principal=asset.principal,
        )
        return AssetHoldingResponse(
            id=asset.id,
            asset_type=asset.asset_type,
            symbol=None,
            name=asset.name,
            quantity=result["paid_count"],
            avg_price=float(asset.monthly_amount),
            current_price=float(asset.monthly_amount),
            exchange_rate=None,
            total_value_krw=result["total_value_krw"],
            total_invested_krw=result["total_paid"],
            profit_loss=result["accrued_interest_aftertax"],
            profit_loss_rate=round(result["accrued_interest_aftertax"] / result["total_paid"] * 100, 2) if result["total_paid"] else 0,
            created_at=asset.created_at,
            interest_rate=float(asset.interest_rate),
            bank_name=asset.bank_name,
            monthly_amount=float(asset.monthly_amount),
            start_date=asset.start_date,
            maturity_date=asset.maturity_date,
            tax_rate=float(asset.tax_rate) if asset.tax_rate else 15.4,
            accrued_interest_pretax=result["accrued_interest_pretax"],
            accrued_interest_aftertax=result["accrued_interest_aftertax"],
            maturity_amount=result["maturity_amount"],
            elapsed_months=result["paid_count"],
            total_months=result["total_months"],
            paid_count=result["paid_count"],
        )

    # --- 파킹통장 ---
    if asset.asset_type == AssetType.PARKING:
        result = calculate_parking_interest(
            principal=asset.principal,
            annual_rate=asset.interest_rate,
            tax_rate=asset.tax_rate or Decimal("15.4"),
        )
        p = float(asset.principal)
        return AssetHoldingResponse(
            id=asset.id,
            asset_type=asset.asset_type,
            symbol=None,
            name=asset.name,
            quantity=1,
            avg_price=p,
            current_price=p,
            exchange_rate=None,
            total_value_krw=result["total_value_krw"],
            total_invested_krw=p,
            profit_loss=0,
            profit_loss_rate=0,
            created_at=asset.created_at,
            interest_rate=float(asset.interest_rate),
            bank_name=asset.bank_name,
            principal=p,
            tax_rate=float(asset.tax_rate) if asset.tax_rate else 15.4,
            daily_interest=result["daily_interest"],
            monthly_interest=result["monthly_interest"],
        )

    # --- 기존 자산 유형 (주식, 금, 현금) ---
    buy_txns = [t for t in asset.transactions if t.type == TransactionType.BUY]
    sell_txns = [t for t in asset.transactions if t.type == TransactionType.SELL]
    deposit_txns = [t for t in asset.transactions if t.type == TransactionType.DEPOSIT]
    withdraw_txns = [t for t in asset.transactions if t.type == TransactionType.WITHDRAW]

    buy_qty = sum(float(t.quantity) for t in buy_txns)
    sell_qty = sum(float(t.quantity) for t in sell_txns)
    deposit_qty = sum(float(t.quantity) for t in deposit_txns)
    withdraw_qty = sum(float(t.quantity) for t in withdraw_txns)
    quantity = buy_qty + deposit_qty - sell_qty - withdraw_qty

    is_foreign = asset.asset_type in (AssetType.STOCK_US, AssetType.CASH_USD)

    if buy_qty > 0:
        if is_foreign:
            avg_price_krw = sum(
                float(t.quantity) * float(t.unit_price) * float(t.exchange_rate or Decimal("1"))
                for t in buy_txns
            ) / buy_qty
        else:
            avg_price_krw = sum(
                float(t.quantity) * float(t.unit_price) for t in buy_txns
            ) / buy_qty
    else:
        avg_price_krw = 0.0

    total_invested_krw = quantity * avg_price_krw

    current_price = 0.0
    current_exchange_rate: float | None = None
    price_cached = True

    if asset.asset_type == AssetType.CASH_KRW:
        current_price = 1.0
        total_value_krw = quantity
        total_invested_krw = quantity
    elif asset.asset_type == AssetType.CASH_USD:
        rate_resp = await market.get_cached_exchange_rate()
        if rate_resp:
            current_price = 1.0
            current_exchange_rate = rate_resp.rate
            total_value_krw = quantity * rate_resp.rate
        else:
            price_cached = False
            current_price = 1.0
            total_value_krw = 0.0
    elif asset.symbol:
        price_resp = await market.get_cached_price(asset.symbol, asset.asset_type)
        if price_resp:
            current_price = price_resp.price
        else:
            price_cached = False
            current_price = 0.0

        if is_foreign:
            rate_resp = await market.get_cached_exchange_rate()
            if rate_resp:
                current_exchange_rate = rate_resp.rate
                total_value_krw = quantity * current_price * rate_resp.rate
            else:
                price_cached = False
                total_value_krw = 0.0
        else:
            total_value_krw = quantity * current_price
    else:
        total_value_krw = 0.0

    profit_loss = total_value_krw - total_invested_krw
    profit_loss_rate = (profit_loss / total_invested_krw * 100) if total_invested_krw > 0 else 0.0

    return AssetHoldingResponse(
        id=asset.id,
        asset_type=asset.asset_type,
        symbol=asset.symbol,
        name=asset.name,
        quantity=round(quantity, 8),
        avg_price=round(avg_price_krw, 4),
        current_price=round(current_price, 4),
        exchange_rate=round(current_exchange_rate, 4) if current_exchange_rate else None,
        total_value_krw=round(total_value_krw, 2),
        total_invested_krw=round(total_invested_krw, 2),
        profit_loss=round(profit_loss, 2),
        profit_loss_rate=round(profit_loss_rate, 2),
        created_at=asset.created_at,
        price_cached=price_cached,
    )
