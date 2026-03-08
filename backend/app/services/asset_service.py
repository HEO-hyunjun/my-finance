import asyncio
import uuid
from datetime import date

from app.core.tz import today as tz_today
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.asset import Asset, AssetType, InterestType
from app.models.budget import Expense
from app.models.income import Income
from app.models.transaction import TransactionType
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
    await db.flush()  # asset.id 확보

    # 적금: 자동이체 연동
    if (
        data.asset_type == AssetType.SAVINGS
        and data.auto_transfer_source_id
        and data.auto_transfer_day
        and data.monthly_amount
    ):
        from app.models.auto_transfer import AutoTransfer

        auto_transfer = AutoTransfer(
            user_id=user_id,
            source_asset_id=data.auto_transfer_source_id,
            target_asset_id=asset.id,
            name=f"{data.name} 자동납입",
            amount=data.monthly_amount,
            transfer_day=data.auto_transfer_day,
        )
        db.add(auto_transfer)

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
    # 고정비 자동 Expense 보장
    from app.services.budget_service import _ensure_auto_expenses_for_range, _get_current_period_for_user
    try:
        ps, pe = await _get_current_period_for_user(db, user_id)
        await _ensure_auto_expenses_for_range(db, user_id, ps, pe)
        await db.flush()
    except Exception:
        pass

    stmt = (
        select(Asset)
        .options(selectinload(Asset.transactions))
        .where(Asset.id == asset_id, Asset.user_id == user_id)
    )
    asset = (await db.execute(stmt)).scalar_one_or_none()
    if not asset:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Asset not found")

    # 지출/수입 합계 조회 (CASH_KRW 동적 잔액 계산용)
    today = tz_today()
    expense_stmt = (
        select(func.coalesce(func.sum(Expense.amount), 0))
        .where(
            Expense.user_id == user_id,
            Expense.source_asset_id == asset_id,
            Expense.spent_at <= today,
        )
    )
    income_stmt = (
        select(func.coalesce(func.sum(Income.amount), 0))
        .where(
            Income.user_id == user_id,
            Income.target_asset_id == asset_id,
            Income.received_at <= today,
        )
    )
    # 고정비 자동 Expense 합계 (PARKING/DEPOSIT 동적 반영용)
    auto_expense_stmt = (
        select(func.coalesce(func.sum(Expense.amount), 0))
        .where(
            Expense.user_id == user_id,
            Expense.source_asset_id == asset_id,
            Expense.spent_at <= today,
            Expense.fixed_expense_id.isnot(None),
        )
    )
    expense_sum = float((await db.execute(expense_stmt)).scalar() or 0)
    income_sum = float((await db.execute(income_stmt)).scalar() or 0)
    auto_expense_sum = float((await db.execute(auto_expense_stmt)).scalar() or 0)

    holding = await _calculate_holding(
        asset, market, expense_sum=expense_sum, income_sum=income_sum,
        auto_expense_sum=auto_expense_sum,
    )
    return holding


async def get_asset_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    market: MarketService,
) -> AssetSummaryResponse:
    # 고정비 자동 Expense 보장 (자산 잔액에 반영되도록)
    from app.services.budget_service import _ensure_auto_expenses_for_range, _get_current_period_for_user
    try:
        ps, pe = await _get_current_period_for_user(db, user_id)
        await _ensure_auto_expenses_for_range(db, user_id, ps, pe)
        await db.flush()
    except Exception:
        pass  # 예산 설정 없어도 자산 조회는 가능

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

    # 시세 캐시 프리워밍: 캐시 미스 시 0원 방지를 위해 필요한 시세를 병렬로 미리 조회
    symbols_needed: set[tuple[str, AssetType | None]] = set()
    needs_exchange_rate = False
    for asset in assets:
        if asset.asset_type in INTEREST_BASED_TYPES or asset.asset_type == AssetType.CASH_KRW:
            continue
        if asset.asset_type in (AssetType.STOCK_US, AssetType.CASH_USD):
            needs_exchange_rate = True
        if asset.symbol:
            symbols_needed.add((asset.symbol, asset.asset_type))

    warm_tasks: list = []
    if needs_exchange_rate:
        warm_tasks.append(market.get_exchange_rate())
    for symbol, atype in symbols_needed:
        warm_tasks.append(market.get_price(symbol, atype))
    if warm_tasks:
        await asyncio.gather(*warm_tasks, return_exceptions=True)

    # 지출/수입 합계 사전 조회 (동적 잔액 계산용)
    today = tz_today()
    expense_stmt = (
        select(Expense.source_asset_id, func.coalesce(func.sum(Expense.amount), 0))
        .where(Expense.user_id == user_id, Expense.spent_at <= today, Expense.source_asset_id.isnot(None))
        .group_by(Expense.source_asset_id)
    )
    expense_rows = (await db.execute(expense_stmt)).all()
    expense_by_asset: dict[uuid.UUID, float] = {row[0]: float(row[1]) for row in expense_rows}

    # 자동 고정비 Expense 합계 (PARKING/DEPOSIT 동적 반영용 - principal에 미반영된 분)
    auto_expense_stmt = (
        select(Expense.source_asset_id, func.coalesce(func.sum(Expense.amount), 0))
        .where(
            Expense.user_id == user_id,
            Expense.spent_at <= today,
            Expense.source_asset_id.isnot(None),
            Expense.fixed_expense_id.isnot(None),
        )
        .group_by(Expense.source_asset_id)
    )
    auto_expense_rows = (await db.execute(auto_expense_stmt)).all()
    auto_expense_by_asset: dict[uuid.UUID, float] = {row[0]: float(row[1]) for row in auto_expense_rows}

    income_stmt = (
        select(Income.target_asset_id, func.coalesce(func.sum(Income.amount), 0))
        .where(Income.user_id == user_id, Income.received_at <= today, Income.target_asset_id.isnot(None))
        .group_by(Income.target_asset_id)
    )
    income_rows = (await db.execute(income_stmt)).all()
    income_by_asset: dict[uuid.UUID, float] = {row[0]: float(row[1]) for row in income_rows}

    for asset in assets:
        holding = await _calculate_holding(
            asset, market,
            expense_sum=expense_by_asset.get(asset.id, 0.0),
            income_sum=income_by_asset.get(asset.id, 0.0),
            auto_expense_sum=auto_expense_by_asset.get(asset.id, 0.0),
        )
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
    asset: Asset, market: MarketService,
    expense_sum: float = 0.0, income_sum: float = 0.0,
    auto_expense_sum: float = 0.0,
) -> AssetHoldingResponse:
    """보유량, 평균단가, 수익률 계산 (이자 기반 자산 포함)"""
    today = tz_today()

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
        effective_value = result["total_value_krw"] - auto_expense_sum
        return AssetHoldingResponse(
            id=asset.id,
            asset_type=asset.asset_type,
            symbol=None,
            name=asset.name,
            quantity=1,
            avg_price=p,
            current_price=p,
            exchange_rate=None,
            total_value_krw=effective_value,
            total_invested_krw=p,
            profit_loss=result["accrued_interest_aftertax"] - auto_expense_sum,
            profit_loss_rate=round((result["accrued_interest_aftertax"] - auto_expense_sum) / p * 100, 2) if p else 0,
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
        effective_principal = Decimal(str(float(asset.principal) - auto_expense_sum))
        result = calculate_parking_interest(
            principal=effective_principal,
            annual_rate=asset.interest_rate,
            tax_rate=asset.tax_rate or Decimal("15.4"),
        )
        p = float(effective_principal)
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

    # 원가 계산: BUY + DEPOSIT 거래 모두 포함 (입금도 매입 원가에 반영)
    cost_txns = buy_txns + deposit_txns
    cost_qty = buy_qty + deposit_qty

    if cost_qty > 0:
        if is_foreign:
            avg_price_krw = sum(
                float(t.quantity) * float(t.unit_price) * float(t.exchange_rate or Decimal("1"))
                for t in cost_txns
            ) / cost_qty
        else:
            avg_price_krw = sum(
                float(t.quantity) * float(t.unit_price) for t in cost_txns
            ) / cost_qty
    else:
        avg_price_krw = 0.0

    total_invested_krw = quantity * avg_price_krw

    current_price = 0.0
    current_exchange_rate: float | None = None
    price_cached = True

    if asset.asset_type == AssetType.CASH_KRW:
        current_price = 1.0
        # 보유량 자체에 지출/수입 반영
        quantity = quantity - expense_sum + income_sum
        total_value_krw = quantity
        total_invested_krw = quantity
    elif asset.asset_type == AssetType.CASH_USD:
        rate_resp = await market.get_exchange_rate()
        current_price = 1.0
        current_exchange_rate = rate_resp.rate
        price_cached = rate_resp.cached
        total_value_krw = quantity * rate_resp.rate
    elif asset.symbol:
        price_resp = await market.get_price(asset.symbol, asset.asset_type)
        current_price = price_resp.price
        price_cached = price_resp.cached

        if is_foreign:
            rate_resp = await market.get_exchange_rate()
            current_exchange_rate = rate_resp.rate
            price_cached = price_cached and rate_resp.cached
            total_value_krw = quantity * current_price * rate_resp.rate
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
