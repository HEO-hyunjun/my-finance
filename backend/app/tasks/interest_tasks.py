import asyncio
import logging
from decimal import Decimal

from app.core.celery_app import celery_app
from app.core.tz import (
    kst_day_utc_range,
    kst_noon_utc,
    today as tz_today,
)

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
                    balance = await get_account_balance(db, account.id, account.currency)
                    if balance <= 0:
                        continue

                    # 중복 체크: 오늘(KST) 이미 기록된 이자 Entry가 있는지 (source 기준)
                    day_start_utc, day_end_utc = kst_day_utc_range(today)
                    existing = await db.execute(
                        select(Entry.id).where(
                            and_(
                                Entry.account_id == account.id,
                                Entry.source == "interest",
                                Entry.transacted_at >= day_start_utc,
                                Entry.transacted_at < day_end_utc,
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
                        source="interest",
                        transacted_at=kst_noon_utc(today),
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
    from sqlalchemy import select, func

    from app.models.account import Account, AccountType
    from app.models.entry import Entry, EntryType
    from app.services.interest_service import calculate_ledger_accrued_interest

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
                    tax_rate = account.tax_rate or Decimal("15.400")

                    # 원장 기반 발생이자 (비-INTEREST entry 각각의 경과일로 단리 계산)
                    ledger = (await db.execute(
                        select(Entry).where(
                            Entry.account_id == account.id,
                            Entry.type != EntryType.INTEREST,
                        )
                    )).scalars().all()
                    if not ledger:
                        continue

                    accrued = calculate_ledger_accrued_interest(
                        ledger,
                        annual_rate=account.interest_rate,
                        tax_rate=tax_rate,
                        as_of=today,
                    )

                    # 이미 기록된 이자 합계와의 차액만 보충 (자기치유 델타)
                    recorded = Decimal(str((await db.execute(
                        select(func.coalesce(func.sum(Entry.amount), 0)).where(
                            Entry.account_id == account.id,
                            Entry.type == EntryType.INTEREST,
                        )
                    )).scalar()))

                    delta = accrued - recorded
                    if delta <= 0:
                        continue

                    # Entry로 월별이자 기록 (원금 업데이트 불필요)
                    entry = Entry(
                        user_id=account.user_id,
                        account_id=account.id,
                        type=EntryType.INTEREST,
                        amount=delta,
                        currency=account.currency,
                        memo=f"{account.name} 월별이자",
                        source="interest",
                        transacted_at=kst_noon_utc(today),
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
