import asyncio
import logging
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from app.core.celery_app import celery_app
from app.core.tz import APP_TZ, today as tz_today


def _kst_day_utc_range(d: date) -> tuple[datetime, datetime]:
    """KST 기준 하루(00:00~다음날 00:00)의 UTC 범위를 반환."""
    start = datetime.combine(d, time.min, tzinfo=APP_TZ).astimezone(timezone.utc)
    end = datetime.combine(d + timedelta(days=1), time.min, tzinfo=APP_TZ).astimezone(timezone.utc)
    return start, end


def _kst_month_utc_range(d: date) -> tuple[datetime, datetime]:
    """KST 기준 이번 달(1일 00:00~다음달 1일 00:00)의 UTC 범위를 반환."""
    month_start = d.replace(day=1)
    if month_start.month == 12:
        next_month = date(month_start.year + 1, 1, 1)
    else:
        next_month = date(month_start.year, month_start.month + 1, 1)
    start = datetime.combine(month_start, time.min, tzinfo=APP_TZ).astimezone(timezone.utc)
    end = datetime.combine(next_month, time.min, tzinfo=APP_TZ).astimezone(timezone.utc)
    return start, end

logger = logging.getLogger(__name__)


def _get_async_session():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session, engine


@celery_app.task(name="app.tasks.interest_tasks.record_daily_parking_interest")
def record_daily_parking_interest():
    """파킹통장/CMA 일일이자를 Entry로 기록 (매일 실행)"""
    return asyncio.run(_record_parking_interest_async())


@celery_app.task(name="app.tasks.interest_tasks.record_monthly_deposit_interest")
def record_monthly_deposit_interest():
    """예금/적금 월별이자를 Entry로 기록 (매월 1일 실행)"""
    return asyncio.run(_record_deposit_interest_async())


async def _record_parking_interest_async():
    from sqlalchemy import select, and_

    from app.models.account import Account, AccountType
    from app.models.entry import Entry, EntryType
    from app.services.entry_service import get_account_balance
    from app.services.interest_service import calculate_parking_interest

    async_session, engine = _get_async_session()
    today = tz_today()
    count = 0

    try:
        async with async_session() as db:
            # 파킹통장/CMA 계좌 조회 (이율이 있는 활성 계좌)
            result = await db.execute(
                select(Account).where(
                    Account.account_type == AccountType.PARKING,
                    Account.is_active.is_(True),
                    Account.interest_rate > 0,
                )
            )
            accounts = result.scalars().all()

            for account in accounts:
                try:
                    # 현재 잔액 조회 (Entry 합계 = 유일한 진실 원천)
                    balance = await get_account_balance(db, account.id)
                    if balance <= 0:
                        continue

                    # 중복 체크: 오늘(KST) 이미 기록된 이자 Entry가 있는지
                    day_start_utc, day_end_utc = _kst_day_utc_range(today)
                    existing = await db.execute(
                        select(Entry.id).where(
                            and_(
                                Entry.account_id == account.id,
                                Entry.type == EntryType.INTEREST,
                                Entry.transacted_at >= day_start_utc,
                                Entry.transacted_at < day_end_utc,
                                Entry.memo.like("%일일이자%"),
                            )
                        ).limit(1)
                    )
                    if existing.first() is not None:
                        continue

                    info = calculate_parking_interest(
                        principal=balance,
                        annual_rate=account.interest_rate,
                        tax_rate=account.tax_rate or Decimal("15.400"),
                    )

                    daily_after_tax = round(
                        info["daily_interest"]
                        * (1 - float(account.tax_rate or Decimal("15.400")) / 100)
                    )
                    if daily_after_tax <= 0:
                        continue

                    after_tax_decimal = Decimal(str(daily_after_tax))

                    # Entry로 이자 기록 (원금 업데이트 불필요 — Entry가 진실 원천)
                    entry = Entry(
                        user_id=account.user_id,
                        account_id=account.id,
                        type=EntryType.INTEREST,
                        amount=after_tax_decimal,
                        currency=account.currency,
                        memo=f"{account.name} 일일이자",
                        transacted_at=datetime.now(timezone.utc),
                    )
                    db.add(entry)
                    count += 1
                except Exception as e:
                    logger.warning(
                        f"Parking interest failed for account {account.id}: {e}"
                    )

            await db.commit()
            logger.info(
                f"Daily parking interest recorded: {count} accounts on {today}"
            )

        return {"recorded": count, "date": str(today)}
    finally:
        await engine.dispose()


async def _record_deposit_interest_async():
    from sqlalchemy import select, and_, func

    from app.models.account import Account, AccountType
    from app.models.entry import Entry, EntryType
    from app.services.interest_service import (
        calculate_deposit_interest,
        calculate_savings_interest,
    )

    async_session, engine = _get_async_session()
    today = tz_today()
    count = 0

    try:
        async with async_session() as db:
            # 예금 + 적금 계좌 조회 (만기 전, 이율 있는 활성 계좌)
            result = await db.execute(
                select(Account).where(
                    Account.account_type.in_(
                        [AccountType.DEPOSIT, AccountType.SAVINGS]
                    ),
                    Account.is_active.is_(True),
                    Account.interest_rate > 0,
                    Account.maturity_date >= today,
                )
            )
            accounts = result.scalars().all()

            for account in accounts:
                try:
                    # 중복 체크: 이번 달(KST) 이미 기록된 월별이자 Entry가 있는지
                    month_start_utc, month_end_utc = _kst_month_utc_range(today)
                    existing = await db.execute(
                        select(Entry.id).where(
                            and_(
                                Entry.account_id == account.id,
                                Entry.type == EntryType.INTEREST,
                                Entry.transacted_at >= month_start_utc,
                                Entry.transacted_at < month_end_utc,
                                Entry.memo.like("%월별이자%"),
                            )
                        ).limit(1)
                    )
                    if existing.first() is not None:
                        continue

                    tax_rate = account.tax_rate or Decimal("15.400")

                    # 원금 계산: 이자 Entry를 제외한 모든 Entry의 합계
                    principal_result = await db.execute(
                        select(
                            func.coalesce(func.sum(Entry.amount), 0)
                        ).where(
                            Entry.account_id == account.id,
                            Entry.type != EntryType.INTEREST,
                        )
                    )
                    principal = Decimal(str(principal_result.scalar()))

                    if principal <= 0:
                        continue

                    if account.account_type == AccountType.DEPOSIT:
                        info = calculate_deposit_interest(
                            principal=principal,
                            annual_rate=account.interest_rate,
                            start_date=account.start_date,
                            as_of_date=today,
                            maturity_date=account.maturity_date,
                            interest_type=(
                                account.interest_type.value
                                if account.interest_type
                                else "simple"
                            ),
                            tax_rate=tax_rate,
                        )
                        prev_month = today.replace(day=1)
                        prev_info = calculate_deposit_interest(
                            principal=principal,
                            annual_rate=account.interest_rate,
                            start_date=account.start_date,
                            as_of_date=prev_month,
                            maturity_date=account.maturity_date,
                            interest_type=(
                                account.interest_type.value
                                if account.interest_type
                                else "simple"
                            ),
                            tax_rate=tax_rate,
                        )
                        monthly_interest = (
                            info["accrued_interest_aftertax"]
                            - prev_info["accrued_interest_aftertax"]
                        )
                    else:
                        # 적금
                        info = calculate_savings_interest(
                            monthly_amount=account.monthly_amount or Decimal("0"),
                            annual_rate=account.interest_rate,
                            start_date=account.start_date,
                            as_of_date=today,
                            maturity_date=account.maturity_date,
                            tax_rate=tax_rate,
                            principal=principal,
                        )
                        prev_month = today.replace(day=1)
                        prev_info = calculate_savings_interest(
                            monthly_amount=account.monthly_amount or Decimal("0"),
                            annual_rate=account.interest_rate,
                            start_date=account.start_date,
                            as_of_date=prev_month,
                            maturity_date=account.maturity_date,
                            tax_rate=tax_rate,
                            principal=principal,
                        )
                        monthly_interest = (
                            info["accrued_interest_aftertax"]
                            - prev_info["accrued_interest_aftertax"]
                        )

                    if monthly_interest <= 0:
                        continue

                    # Entry로 월별이자 기록 (원금 업데이트 불필요)
                    entry = Entry(
                        user_id=account.user_id,
                        account_id=account.id,
                        type=EntryType.INTEREST,
                        amount=Decimal(str(monthly_interest)),
                        currency=account.currency,
                        memo=f"{account.name} 월별이자",
                        transacted_at=datetime.now(timezone.utc),
                    )
                    db.add(entry)
                    count += 1
                except Exception as e:
                    logger.warning(
                        f"Deposit interest failed for account {account.id}: {e}"
                    )

            await db.commit()
            logger.info(
                f"Monthly deposit/savings interest recorded: {count} accounts on {today}"
            )

        return {"recorded": count, "date": str(today)}
    finally:
        await engine.dispose()
