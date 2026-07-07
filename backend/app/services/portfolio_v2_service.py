import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType
from app.models.security import Security
from app.services.entry_service import (
    get_account_balance,
    get_cash_balances_by_currency,
    get_holdings,
)
from app.services.security_service import get_latest_price, get_exchange_rate

# 리밸런싱 자산 분류 도메인 (부채 제외)
ASSET_BREAKDOWN_DOMAINS = ("cash", "deposit", "equity_kr", "equity_us", "commodity")
LIABILITY_ACCOUNT_TYPES = (AccountType.LOAN, AccountType.CREDIT_CARD)


async def get_total_assets(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """전체 자산 현황: 계좌별 잔액 + 투자 계좌의 시세 평가"""
    stmt = select(Account).where(Account.user_id == user_id, Account.is_active.is_(True))
    accounts = (await db.execute(stmt)).scalars().all()

    krw_rate = await get_exchange_rate(db, "USD", "KRW") or Decimal("1380")
    total_krw = Decimal("0")
    total_debt_krw = Decimal("0")
    account_details = []

    for account in accounts:
        balance = await get_account_balance(db, account.id, account.currency)

        if account.account_type == AccountType.INVESTMENT:
            # 투자 계좌: 현금 + 종목별 시가 평가
            holdings = await get_holdings(db, account.id)
            holdings_value_krw = Decimal("0")

            for h in holdings:
                price_record = await get_latest_price(db, uuid.UUID(h["security_id"]))
                if price_record:
                    value = h["quantity"] * Decimal(str(price_record.close_price))
                    value_krw = value * krw_rate if price_record.currency == "USD" else value
                    holdings_value_krw += value_krw
                    h["current_price"] = Decimal(str(price_record.close_price))
                    h["value_krw"] = value_krw

            # 현금은 통화별로 집계 후 KRW 환산 (USD 현금 누락 방지)
            cash_krw = Decimal("0")
            for cur, bal in (await get_cash_balances_by_currency(db, account.id)).items():
                cash_krw += bal * krw_rate if cur != "KRW" else bal

            total_value = cash_krw + holdings_value_krw

            account_details.append({
                "id": str(account.id),
                "name": account.name,
                "account_type": account.account_type.value,
                "currency": account.currency,
                "cash_balance": balance,
                "holdings_value": holdings_value_krw,
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
            if account.account_type in LIABILITY_ACCOUNT_TYPES:
                total_debt_krw += -value_krw  # 음수 잔액 → 양수 부채

    return {
        "total_krw": total_krw,
        "net_worth_krw": total_krw,
        "total_debt_krw": total_debt_krw,
        "total_assets_krw": total_krw + total_debt_krw,
        "accounts": account_details,
        "exchange_rate_usd_krw": krw_rate,
    }


async def get_asset_breakdown(db: AsyncSession, user_id: uuid.UUID) -> dict[str, float]:
    """자산 분류 breakdown (KRW) — 리밸런싱·스냅샷의 단일 진실 함수.

    도메인: cash | deposit | equity_kr | equity_us | commodity.
    - cash/parking 계좌 + 투자계좌 현금 → cash
    - deposit/savings → deposit
    - 보유 종목 평가액 → Security.asset_class 그대로
    - 부채(loan/credit_card)는 breakdown에서 제외 (순자산에서 음수로만 반영)
    """
    accounts = (await db.execute(
        select(Account).where(Account.user_id == user_id, Account.is_active.is_(True))
    )).scalars().all()

    krw_rate = await get_exchange_rate(db, "USD", "KRW") or Decimal("1380")
    breakdown: dict[str, Decimal] = {}

    def _add(key: str, value: Decimal) -> None:
        breakdown[key] = breakdown.get(key, Decimal("0")) + value

    for account in accounts:
        if account.account_type in LIABILITY_ACCOUNT_TYPES:
            continue

        if account.account_type == AccountType.INVESTMENT:
            # 투자계좌 현금은 통화별로 집계 후 KRW 환산 (USD 현금 누락 방지)
            for cur, bal in (await get_cash_balances_by_currency(db, account.id)).items():
                _add("cash", bal * krw_rate if cur != "KRW" else bal)

            for h in await get_holdings(db, account.id):
                sec_id = uuid.UUID(h["security_id"])
                price = await get_latest_price(db, sec_id)
                if price:
                    value = h["quantity"] * Decimal(str(price.close_price))
                    currency = price.currency
                else:
                    value = h["quantity"] * h["avg_price"]
                    currency = h["currency"]
                value_krw = value * krw_rate if currency == "USD" else value
                sec = await db.get(Security, sec_id)
                domain = sec.asset_class.value if sec else "equity_kr"
                _add(domain, value_krw)
        else:
            balance = await get_account_balance(db, account.id, account.currency)
            balance_krw = balance * krw_rate if account.currency == "USD" else balance
            if account.account_type in (AccountType.CASH, AccountType.PARKING):
                _add("cash", balance_krw)
            elif account.account_type in (AccountType.DEPOSIT, AccountType.SAVINGS):
                _add("deposit", balance_krw)

    return {k: float(v) for k, v in breakdown.items() if v != 0}


async def get_asset_allocation(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    """자산 배분 (breakdown 도메인별 비율)"""
    breakdown = await get_asset_breakdown(db, user_id)
    total = sum(breakdown.values())
    if total <= 0:
        return []

    return [
        {"type": k, "value_krw": Decimal(str(v)), "ratio": v / total}
        for k, v in breakdown.items()
    ]
