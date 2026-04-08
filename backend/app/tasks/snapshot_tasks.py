import asyncio
import logging

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


@celery_app.task(name="app.tasks.snapshot_tasks.take_daily_snapshot")
def take_daily_snapshot():
    return asyncio.run(_take_snapshot_async())


async def _take_snapshot_async():
    from sqlalchemy import select, and_
    from app.models.account import Account, AccountType
    from app.models.portfolio import AccountSnapshot
    from app.services.entry_service import get_account_balance
    from app.services.security_service import get_latest_price
    from app.services.entry_service import get_holdings

    async_session, engine = _get_async_session()
    today = tz_today()
    count = 0

    try:
        async with async_session() as db:
            # 모든 활성 계좌
            accounts = (await db.execute(
                select(Account).where(Account.is_active.is_(True))
            )).scalars().all()

            for account in accounts:
                try:
                    # 중복 체크
                    existing = (await db.execute(
                        select(AccountSnapshot).where(and_(
                            AccountSnapshot.account_id == account.id,
                            AccountSnapshot.snapshot_date == today,
                        ))
                    )).scalar_one_or_none()
                    if existing:
                        continue

                    balance = await get_account_balance(db, account.id)

                    # 투자 계좌는 holdings도 저장
                    holdings_json = None
                    if account.account_type == AccountType.INVESTMENT:
                        holdings = await get_holdings(db, account.id)
                        holdings_json = {}
                        for h in holdings:
                            price = await get_latest_price(db, h["security_id"]) if h.get("security_id") else None
                            holdings_json[h.get("symbol", "unknown")] = {
                                "quantity": str(h["quantity"]),
                                "price": str(price.close_price) if price else None,
                            }

                    snapshot = AccountSnapshot(
                        account_id=account.id,
                        user_id=account.user_id,
                        snapshot_date=today,
                        balance=balance,
                        currency=account.currency,
                        holdings=holdings_json,
                    )
                    db.add(snapshot)
                    count += 1
                except Exception as e:
                    logger.warning(f"Snapshot failed for account {account.id}: {e}")

            await db.commit()
            logger.info(f"Daily snapshots taken: {count} accounts")
    finally:
        await engine.dispose()

    return {"snapshots": count, "date": str(today)}
