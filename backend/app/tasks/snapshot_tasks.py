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
    import uuid as _uuid
    from decimal import Decimal
    from sqlalchemy import select, and_
    from app.models.account import Account, AccountType
    from app.models.portfolio import AccountSnapshot, AssetSnapshot
    from app.services.entry_service import get_account_balance, get_holdings
    from app.services.security_service import get_latest_price, get_exchange_rate

    async_session, engine = _get_async_session()
    today = tz_today()
    count = 0

    try:
        async with async_session() as db:
            # 모든 활성 계좌
            accounts = (await db.execute(
                select(Account).where(Account.is_active.is_(True))
            )).scalars().all()

            # 환율 조회
            krw_rate = await get_exchange_rate(db, "USD", "KRW") or Decimal("1380")

            # 유저별 자산 집계용
            user_totals: dict[str, dict] = {}

            for account in accounts:
                try:
                    balance = await get_account_balance(db, account.id)

                    # 투자 계좌는 holdings도 저장
                    holdings_json = None
                    if account.account_type == AccountType.INVESTMENT:
                        holdings = await get_holdings(db, account.id)
                        holdings_json = {}
                        holdings_value_krw = Decimal("0")
                        for h in holdings:
                            sec_id = h.get("security_id")
                            price = await get_latest_price(db, _uuid.UUID(sec_id) if isinstance(sec_id, str) else sec_id) if sec_id else None
                            holdings_json[h.get("symbol", "unknown")] = {
                                "quantity": str(h["quantity"]),
                                "price": str(price.close_price) if price else None,
                            }
                            if price:
                                value = h["quantity"] * Decimal(str(price.close_price))
                                if price.currency == "USD":
                                    value *= krw_rate
                                holdings_value_krw += value
                        cash_krw = balance * krw_rate if account.currency == "USD" else balance
                        account_total_krw = cash_krw + holdings_value_krw
                    elif account.currency == "USD":
                        account_total_krw = balance * krw_rate
                    else:
                        account_total_krw = balance

                    # AccountSnapshot upsert
                    existing = (await db.execute(
                        select(AccountSnapshot).where(and_(
                            AccountSnapshot.account_id == account.id,
                            AccountSnapshot.snapshot_date == today,
                        ))
                    )).scalar_one_or_none()
                    if existing:
                        existing.balance = balance
                        existing.holdings = holdings_json
                    else:
                        db.add(AccountSnapshot(
                            account_id=account.id,
                            user_id=account.user_id,
                            snapshot_date=today,
                            balance=balance,
                            currency=account.currency,
                            holdings=holdings_json,
                        ))
                        count += 1

                    # 유저별 집계 (항상 포함)
                    uid = str(account.user_id)
                    if uid not in user_totals:
                        user_totals[uid] = {"total_krw": Decimal("0"), "breakdown": {}}
                    user_totals[uid]["total_krw"] += account_total_krw
                    atype = account.account_type.value
                    user_totals[uid]["breakdown"][atype] = float(
                        user_totals[uid]["breakdown"].get(atype, 0) + float(account_total_krw)
                    )
                except Exception as e:
                    logger.warning(f"Snapshot failed for account {account.id}: {e}")

            # AssetSnapshot (유저별 총 자산) 저장
            from app.services import portfolio_service

            for uid, data in user_totals.items():
                try:
                    user_uuid = _uuid.UUID(uid)
                    existing_asset = (await db.execute(
                        select(AssetSnapshot).where(and_(
                            AssetSnapshot.user_id == user_uuid,
                            AssetSnapshot.snapshot_date == today,
                        ))
                    )).scalar_one_or_none()
                    if existing_asset:
                        existing_asset.total_krw = data["total_krw"]
                        existing_asset.breakdown = data["breakdown"]
                    else:
                        db.add(AssetSnapshot(
                            user_id=user_uuid,
                            snapshot_date=today,
                            total_krw=data["total_krw"],
                            breakdown=data["breakdown"],
                        ))

                    # 리밸런싱 편차 체크 후 알림 생성
                    try:
                        await portfolio_service.check_and_create_alert(
                            db, user_uuid, today, data["breakdown"], 0.05
                        )
                    except Exception as e:
                        logger.warning(f"Alert check failed for user {uid}: {e}")
                except Exception as e:
                    logger.warning(f"AssetSnapshot failed for user {uid}: {e}")

            await db.commit()
            logger.info(f"Daily snapshots taken: {count} accounts, {len(user_totals)} users")
    finally:
        await engine.dispose()

    return {"snapshots": count, "users": len(user_totals), "date": str(today)}
