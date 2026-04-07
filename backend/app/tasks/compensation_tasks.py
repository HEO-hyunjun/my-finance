"""서버 시작 시 이번 달 누락된 정기 작업을 DB 기반으로 보상 실행하는 태스크.

각 항목의 실행일(recurring_day, transfer_day, payment_day, salary_day)이
이미 지났는데 해당 기록이 없으면 누락으로 판단하고 생성한다.
모든 항목에 중복 방지 로직이 있으므로 안전하게 재실행 가능.
"""

import asyncio
import calendar
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.core.celery_app import celery_app
from app.core.tz import today as tz_today

logger = logging.getLogger(__name__)


def _get_async_session():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session, engine


@celery_app.task(name="app.tasks.compensation_tasks.compensate_missed_tasks")
def compensate_missed_tasks():
    """이번 달 누락된 정기 수입 / 자동이체 / 고정비 / 할부를 보상 실행"""
    return asyncio.run(_compensate_all())


async def _compensate_all():
    async_session, engine = _get_async_session()
    today = tz_today()
    results = {}

    try:
        async with async_session() as db:
            results["recurring_incomes"] = await _compensate_recurring_incomes(db, today)
            results["auto_transfers"] = await _compensate_auto_transfers(db, today)
            results["fixed_expenses"] = await _compensate_fixed_expenses(db, today)
            results["installments"] = await _compensate_installments(db, today)
            results["parking_interest"] = await _compensate_parking_interest(db, today)
            await db.commit()
    finally:
        await engine.dispose()

    logger.info(f"Compensation completed: {results}")
    return results


# ── 1. 정기 수입 보상 ──

async def _compensate_recurring_incomes(db, today: date) -> dict:
    from sqlalchemy import select, extract
    from app.models.income import Income, RecurringIncome

    # recurring_day가 오늘 이전(포함)인 활성 템플릿 전체 조회
    stmt = select(RecurringIncome).where(
        RecurringIncome.is_active.is_(True),
        RecurringIncome.recurring_day <= today.day,
    )
    templates = (await db.execute(stmt)).scalars().all()

    created = 0
    for tmpl in templates:
        # 이번 달 해당 템플릿의 수입이 이미 있는지
        check_stmt = select(Income.id).where(
            Income.recurring_income_id == tmpl.id,
            extract("year", Income.received_at) == today.year,
            extract("month", Income.received_at) == today.month,
        )
        if (await db.execute(check_stmt)).scalar_one_or_none():
            continue

        _, last_day = calendar.monthrange(today.year, today.month)
        recv_day = min(tmpl.recurring_day, last_day)

        db.add(Income(
            user_id=tmpl.user_id,
            type=tmpl.type,
            amount=tmpl.amount,
            description=tmpl.description,
            recurring_income_id=tmpl.id,
            target_asset_id=tmpl.target_asset_id,
            received_at=date(today.year, today.month, recv_day),
        ))
        created += 1

    logger.info(f"[보상] 정기 수입: {created}건 생성")
    return {"created": created}


# ── 2. 자동이체 보상 ──

async def _compensate_auto_transfers(db, today: date) -> dict:
    from sqlalchemy import select, extract
    from sqlalchemy.orm import selectinload
    from app.models.auto_transfer import AutoTransfer
    from app.models.transaction import Transaction
    from app.schemas.transaction import TransactionCreate
    from app.services.transfer_service import execute_transfer
    from app.services.transaction_service import create_transaction

    _DEPOSIT_TYPES = {"deposit", "savings"}

    # transfer_day가 오늘 이전(포함)인 활성 자동이체 전체 조회
    stmt = (
        select(AutoTransfer)
        .where(
            AutoTransfer.is_active.is_(True),
            AutoTransfer.transfer_day <= today.day,
        )
        .options(selectinload(AutoTransfer.target_asset))
    )
    items = (await db.execute(stmt)).scalars().all()

    executed = 0
    for item in items:
        # 이번 달 해당 자동이체의 트랜잭션이 있는지 (memo 기반)
        memo = f"[자동이체] {item.name}"
        check_stmt = select(Transaction.id).where(
            Transaction.user_id == item.user_id,
            Transaction.memo == memo,
            extract("year", Transaction.transacted_at) == today.year,
            extract("month", Transaction.transacted_at) == today.month,
        )
        if (await db.execute(check_stmt)).first():
            continue

        try:
            target_type = item.target_asset.asset_type.value if item.target_asset else None

            _, last_day = calendar.monthrange(today.year, today.month)
            tx_day = min(item.transfer_day, last_day)
            tx_at = datetime(today.year, today.month, tx_day, tzinfo=timezone.utc)

            if target_type in _DEPOSIT_TYPES:
                await create_transaction(
                    db=db,
                    user_id=item.user_id,
                    data=TransactionCreate(
                        asset_id=item.target_asset_id,
                        type="deposit",
                        quantity=item.amount,
                        unit_price=Decimal("1"),
                        currency="KRW",
                        fee=Decimal("0"),
                        source_asset_id=item.source_asset_id,
                        memo=memo,
                        transacted_at=tx_at,
                    ),
                )
            else:
                await execute_transfer(
                    db=db,
                    user_id=item.user_id,
                    source_asset_id=item.source_asset_id,
                    target_asset_id=item.target_asset_id,
                    amount=item.amount,
                    memo=memo,
                )
            executed += 1
        except Exception as e:
            logger.warning(f"[보상] 자동이체 실패: {item.id} ({item.name}): {e}")

    logger.info(f"[보상] 자동이체: {executed}건 실행")
    return {"executed": executed}


# ── 3. 고정비 보상 ──

async def _compensate_fixed_expenses(db, today: date) -> dict:
    from sqlalchemy import select
    from app.models.budget import FixedExpense, Expense
    from app.models.user import User
    from app.services.budget_period import get_budget_period

    # salary_day가 오늘 이전(포함)인 유저 = 이번 기간이 이미 시작된 유저
    stmt = select(User).where(User.salary_day <= today.day)
    users = (await db.execute(stmt)).scalars().all()

    created = 0
    for user in users:
        period_start, _ = get_budget_period(today, user.salary_day)

        fe_stmt = select(FixedExpense).where(
            FixedExpense.user_id == user.id,
            FixedExpense.is_active.is_(True),
        )
        fixed_expenses = (await db.execute(fe_stmt)).scalars().all()

        for fe in fixed_expenses:
            check_stmt = select(Expense.id).where(
                Expense.fixed_expense_id == fe.id,
                Expense.spent_at == period_start,
            )
            if (await db.execute(check_stmt)).scalar_one_or_none():
                continue

            db.add(Expense(
                user_id=fe.user_id,
                category_id=fe.category_id,
                amount=fe.amount,
                memo=f"[고정] {fe.name}",
                source_asset_id=fe.source_asset_id,
                fixed_expense_id=fe.id,
                spent_at=period_start,
            ))
            created += 1

    logger.info(f"[보상] 고정비: {created}건 생성 ({len(users)}명)")
    return {"created": created, "users": len(users)}


# ── 4. 할부 보상 ──

async def _compensate_installments(db, today: date) -> dict:
    from sqlalchemy import select, extract
    from app.models.budget import Installment, Expense

    # payment_day가 오늘 이전(포함)인 활성 할부
    stmt = select(Installment).where(
        Installment.is_active.is_(True),
        Installment.payment_day <= today.day,
    )
    installments = (await db.execute(stmt)).scalars().all()

    deducted = 0
    for inst in installments:
        if inst.paid_installments >= inst.total_installments:
            continue

        # 이번 달 해당 할부의 지출이 있는지
        check_stmt = select(Expense.id).where(
            Expense.user_id == inst.user_id,
            Expense.memo.like(f"[자동할부] {inst.name} (%"),
            extract("year", Expense.spent_at) == today.year,
            extract("month", Expense.spent_at) == today.month,
        )
        if (await db.execute(check_stmt)).first():
            continue

        _, last_day = calendar.monthrange(today.year, today.month)
        pay_day = min(inst.payment_day, last_day)

        description = f"[자동할부] {inst.name} ({inst.paid_installments + 1}/{inst.total_installments})"
        db.add(Expense(
            user_id=inst.user_id,
            category_id=inst.category_id,
            amount=inst.monthly_amount,
            memo=description,
            source_asset_id=inst.source_asset_id,
            spent_at=date(today.year, today.month, pay_day),
        ))

        inst.paid_installments += 1
        if inst.paid_installments >= inst.total_installments:
            inst.is_active = False

        deducted += 1

    logger.info(f"[보상] 할부: {deducted}건 차감")
    return {"deducted": deducted}


# ── 5. 파킹이자 백필 ──

async def _compensate_parking_interest(db, today: date) -> dict:
    """누락된 파킹이자를 마지막 기록일 다음날부터 오늘까지 순차 계산.

    복리 구조이므로 날짜 순서대로 원금에 이자를 반영해야 한다.
    다른 보상(자동이체 등)이 원금을 변경할 수 있어 가장 마지막에 실행.
    """
    from sqlalchemy import select, func, and_
    from app.models.asset import Asset, AssetType
    from app.models.income import Income, IncomeType
    from app.services.interest_service import calculate_parking_interest

    result = await db.execute(
        select(Asset).where(
            Asset.asset_type == AssetType.PARKING,
            Asset.principal > 0,
            Asset.interest_rate > 0,
        )
    )
    assets = result.scalars().all()

    total_created = 0
    for asset in assets:
        try:
            # 마지막 이자 기록일 조회
            last_stmt = select(func.max(Income.received_at)).where(
                and_(
                    Income.user_id == asset.user_id,
                    Income.target_asset_id == asset.id,
                    Income.type == IncomeType.INVESTMENT,
                    Income.description.like("%일일이자%"),
                )
            )
            last_date = (await db.execute(last_stmt)).scalar_one_or_none()

            if last_date is None or last_date >= today:
                continue

            # 마지막 기록 다음날부터 오늘까지 순차 계산
            current_principal = Decimal(str(asset.principal or 0))
            current_date = last_date + timedelta(days=1)
            asset_created = 0

            while current_date <= today:
                info = calculate_parking_interest(
                    principal=current_principal,
                    annual_rate=asset.interest_rate,
                    tax_rate=asset.tax_rate or Decimal("15.400"),
                )

                tax_rate_float = float(asset.tax_rate or Decimal("15.400")) / 100
                daily_after_tax = round(info["daily_interest"] * (1 - tax_rate_float))
                if daily_after_tax > 0:
                    after_tax_decimal = Decimal(str(daily_after_tax))

                    db.add(Income(
                        user_id=asset.user_id,
                        type=IncomeType.INVESTMENT,
                        amount=after_tax_decimal,
                        description=f"{asset.name} 일일이자",
                        target_asset_id=asset.id,
                        received_at=current_date,
                    ))

                    current_principal += after_tax_decimal
                    asset_created += 1

                current_date += timedelta(days=1)

            # 최종 원금 반영
            if asset_created > 0:
                asset.principal = current_principal
                total_created += asset_created

        except Exception as e:
            logger.warning(f"[보상] 파킹이자 백필 실패: asset {asset.id}: {e}")

    logger.info(f"[보상] 파킹이자: {total_created}건 백필 ({len(assets)}개 자산)")
    return {"created": total_created, "assets": len(assets)}
