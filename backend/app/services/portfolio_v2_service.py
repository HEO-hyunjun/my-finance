import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType
from app.services.entry_service import get_account_balance, get_holdings
from app.services.security_service import get_latest_price, get_exchange_rate


async def get_total_assets(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """전체 자산 현황: 계좌별 잔액 + 투자 계좌의 시세 평가"""
    stmt = select(Account).where(Account.user_id == user_id, Account.is_active.is_(True))
    accounts = (await db.execute(stmt)).scalars().all()

    krw_rate = await get_exchange_rate(db, "USD", "KRW") or Decimal("1380")
    total_krw = Decimal("0")
    account_details = []

    for account in accounts:
        balance = await get_account_balance(db, account.id)

        if account.account_type == AccountType.INVESTMENT:
            # 투자 계좌: 현금 + 종목별 시가 평가
            holdings = await get_holdings(db, account.id)
            holdings_value = Decimal("0")

            for h in holdings:
                price_record = await get_latest_price(db, uuid.UUID(h["security_id"]))
                if price_record:
                    value = h["quantity"] * Decimal(str(price_record.close_price))
                    if price_record.currency == "USD":
                        value *= krw_rate
                    holdings_value += value
                    h["current_price"] = Decimal(str(price_record.close_price))
                    h["value_krw"] = value

            # 현금잔액 = security_id가 없는 entry들의 amount 합
            # (매매 entry는 security_id가 있으므로 제외됨)
            # amount는 항상 현금 흐름을 나타냄 (BUY=-cost, SELL=+proceeds)
            # 따라서 전체 amount 합계 = 현금 잔액
            cash_balance = balance  # balance = sum(all amounts) = 현금 잔액

            total_value = cash_balance + holdings_value
            if account.currency == "USD":
                total_value *= krw_rate

            account_details.append({
                "id": str(account.id),
                "name": account.name,
                "account_type": account.account_type.value,
                "currency": account.currency,
                "cash_balance": cash_balance,
                "holdings_value": holdings_value,
                "total_value_krw": total_value,
                "holdings": holdings,
            })
            total_krw += total_value
        else:
            # 비투자 계좌: 잔액 그대로
            value_krw = balance
            if account.currency == "USD":
                value_krw = balance * krw_rate

            account_details.append({
                "id": str(account.id),
                "name": account.name,
                "account_type": account.account_type.value,
                "currency": account.currency,
                "balance": balance,
                "total_value_krw": value_krw,
            })
            total_krw += value_krw

    return {
        "total_krw": total_krw,
        "accounts": account_details,
        "exchange_rate_usd_krw": krw_rate,
    }


async def get_asset_allocation(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    """자산 배분 (account_type별 비율)"""
    total_data = await get_total_assets(db, user_id)
    total = total_data["total_krw"]
    if total == 0:
        return []

    allocation: dict[str, Decimal] = {}
    for acc in total_data["accounts"]:
        atype = acc["account_type"]
        allocation[atype] = allocation.get(atype, Decimal("0")) + acc["total_value_krw"]

    return [
        {"type": k, "value_krw": v, "ratio": float(v / total)}
        for k, v in allocation.items()
    ]
