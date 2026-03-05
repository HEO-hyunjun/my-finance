import asyncio
import logging
from datetime import date

from app.core.tz import today as tz_today
from decimal import Decimal

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.interest_tasks.record_daily_parking_interest")
def record_daily_parking_interest():
    """파킹통장/CMA 일일이자를 수입으로 기록 (매일 실행)"""
    return asyncio.run(_record_parking_interest_async())


@celery_app.task(name="app.tasks.interest_tasks.record_monthly_deposit_interest")
def record_monthly_deposit_interest():
    """예금/적금 월별이자를 수입으로 기록 (매월 1일 실행)"""
    return asyncio.run(_record_deposit_interest_async())


async def _record_parking_interest_async():
    from sqlalchemy import select, and_
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    from app.core.config import settings
    from app.models.asset import Asset, AssetType
    from app.models.income import Income, IncomeType
    from app.services.interest_service import calculate_parking_interest

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    today = tz_today()
    count = 0

    async with async_session() as db:
        # 파킹통장/CMA 자산 조회
        result = await db.execute(
            select(Asset).where(
                Asset.asset_type == AssetType.PARKING,
                Asset.principal > 0,
                Asset.interest_rate > 0,
            )
        )
        assets = result.scalars().all()

        for asset in assets:
            try:
                # 중복 체크: 오늘 이미 기록된 이자가 있는지
                existing = await db.execute(
                    select(Income).where(
                        and_(
                            Income.user_id == asset.user_id,
                            Income.target_asset_id == asset.id,
                            Income.received_at == today,
                            Income.type == IncomeType.INVESTMENT,
                            Income.description.like("%일일이자%"),
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                info = calculate_parking_interest(
                    principal=asset.principal,
                    annual_rate=asset.interest_rate,
                    tax_rate=asset.tax_rate or Decimal("15.400"),
                )

                daily_after_tax = round(info["daily_interest"] * (1 - float(asset.tax_rate or Decimal("15.400")) / 100))
                if daily_after_tax <= 0:
                    continue

                # 수입 기록 (target_asset_id 연결 → 원금에 이자 반영)
                income = Income(
                    user_id=asset.user_id,
                    type=IncomeType.INVESTMENT,
                    amount=Decimal(str(daily_after_tax)),
                    description=f"{asset.name} 일일이자",
                    is_recurring=True,
                    target_asset_id=asset.id,
                    received_at=today,
                )
                db.add(income)

                # 원금에 이자 반영
                asset.principal = (asset.principal or Decimal("0")) + Decimal(str(daily_after_tax))
                count += 1
            except Exception as e:
                logger.warning(f"Parking interest failed for asset {asset.id}: {e}")

        await db.commit()
        logger.info(f"Daily parking interest recorded: {count} assets on {today}")

    await engine.dispose()
    return {"recorded": count, "date": str(today)}


async def _record_deposit_interest_async():
    from sqlalchemy import select, and_
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    from app.core.config import settings
    from app.models.asset import Asset, AssetType
    from app.models.income import Income, IncomeType
    from app.services.interest_service import (
        calculate_deposit_interest,
        calculate_savings_interest,
    )

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    today = tz_today()
    count = 0

    async with async_session() as db:
        # 예금 + 적금 자산 조회 (만기 전, 이율 있는 것만)
        result = await db.execute(
            select(Asset).where(
                Asset.asset_type.in_([AssetType.DEPOSIT, AssetType.SAVINGS]),
                Asset.principal > 0,
                Asset.interest_rate > 0,
                Asset.maturity_date >= today,
            )
        )
        assets = result.scalars().all()

        for asset in assets:
            try:
                # 중복 체크: 이번 달 이미 기록된 이자가 있는지
                month_start = today.replace(day=1)
                existing = await db.execute(
                    select(Income).where(
                        and_(
                            Income.user_id == asset.user_id,
                            Income.target_asset_id == asset.id,
                            Income.received_at >= month_start,
                            Income.type == IncomeType.INVESTMENT,
                            Income.description.like("%월별이자%"),
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                tax_rate = asset.tax_rate or Decimal("15.400")

                if asset.asset_type == AssetType.DEPOSIT:
                    info = calculate_deposit_interest(
                        principal=asset.principal,
                        annual_rate=asset.interest_rate,
                        start_date=asset.start_date,
                        as_of_date=today,
                        maturity_date=asset.maturity_date,
                        interest_type=asset.interest_type.value if asset.interest_type else "simple",
                        tax_rate=tax_rate,
                    )
                    # 이번 달 이자 = 현재 경과 이자 - 전월 경과 이자
                    prev_month = today.replace(day=1)
                    prev_info = calculate_deposit_interest(
                        principal=asset.principal,
                        annual_rate=asset.interest_rate,
                        start_date=asset.start_date,
                        as_of_date=prev_month,
                        maturity_date=asset.maturity_date,
                        interest_type=asset.interest_type.value if asset.interest_type else "simple",
                        tax_rate=tax_rate,
                    )
                    monthly_interest = info["accrued_interest_aftertax"] - prev_info["accrued_interest_aftertax"]
                else:
                    # 적금
                    info = calculate_savings_interest(
                        monthly_amount=asset.monthly_amount or Decimal("0"),
                        annual_rate=asset.interest_rate,
                        start_date=asset.start_date,
                        as_of_date=today,
                        maturity_date=asset.maturity_date,
                        tax_rate=tax_rate,
                        principal=asset.principal,
                    )
                    prev_month = today.replace(day=1)
                    prev_info = calculate_savings_interest(
                        monthly_amount=asset.monthly_amount or Decimal("0"),
                        annual_rate=asset.interest_rate,
                        start_date=asset.start_date,
                        as_of_date=prev_month,
                        maturity_date=asset.maturity_date,
                        tax_rate=tax_rate,
                        principal=asset.principal,
                    )
                    monthly_interest = info["accrued_interest_aftertax"] - prev_info["accrued_interest_aftertax"]

                if monthly_interest <= 0:
                    continue

                # 수입 기록 (원금 변동 없이 기록만)
                income = Income(
                    user_id=asset.user_id,
                    type=IncomeType.INVESTMENT,
                    amount=Decimal(str(monthly_interest)),
                    description=f"{asset.name} 월별이자",
                    is_recurring=True,
                    target_asset_id=asset.id,
                    received_at=today,
                )
                db.add(income)
                count += 1
            except Exception as e:
                logger.warning(f"Deposit interest failed for asset {asset.id}: {e}")

        await db.commit()
        logger.info(f"Monthly deposit/savings interest recorded: {count} assets on {today}")

    await engine.dispose()
    return {"recorded": count, "date": str(today)}
