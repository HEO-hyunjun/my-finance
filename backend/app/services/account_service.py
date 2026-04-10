import uuid
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType
from app.models.security import Security, SecurityPrice
from app.services.entry_service import get_account_balance, get_cash_balances_by_currency, get_holdings


async def create_account(db: AsyncSession, user_id: uuid.UUID, data: dict) -> Account:
    account = Account(user_id=user_id, **data)
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


async def get_accounts(db: AsyncSession, user_id: uuid.UUID) -> list[Account]:
    stmt = select(Account).where(Account.user_id == user_id).order_by(Account.created_at)
    return list((await db.execute(stmt)).scalars().all())


async def get_account(db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID) -> Account:
    stmt = select(Account).where(Account.id == account_id, Account.user_id == user_id)
    account = (await db.execute(stmt)).scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


async def update_account(db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID, data: dict) -> Account:
    account = await get_account(db, user_id, account_id)
    for field, value in data.items():
        setattr(account, field, value)
    await db.commit()
    await db.refresh(account)
    return account


async def delete_account(db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID) -> None:
    account = await get_account(db, user_id, account_id)
    await db.delete(account)
    await db.commit()


async def get_account_summary(db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID) -> dict:
    """계좌 요약: 잔액 + 보유 종목 (투자 계좌)"""
    account = await get_account(db, user_id, account_id)
    balance = await get_account_balance(db, account_id)

    result = {
        "id": str(account.id),
        "name": account.name,
        "account_type": account.account_type.value,
        "currency": account.currency,
        "balance": balance,
    }

    if account.account_type == AccountType.INVESTMENT:
        # 통화별 현금 잔액
        cash_by_currency = await get_cash_balances_by_currency(db, account_id)
        holdings = await get_holdings(db, account_id)

        # USD→KRW 환율 조회
        fx_rate = Decimal("1")
        fx_stmt = (
            select(Security.id)
            .where(Security.symbol.in_(["USDKRW=X", "KRW=X"]))
            .limit(1)
        )
        fx_sec = (await db.execute(fx_stmt)).scalar_one_or_none()
        if fx_sec:
            fx_price_stmt = (
                select(SecurityPrice.close_price)
                .where(SecurityPrice.security_id == fx_sec)
                .order_by(SecurityPrice.price_date.desc())
                .limit(1)
            )
            fx_price = (await db.execute(fx_price_stmt)).scalar_one_or_none()
            if fx_price:
                fx_rate = Decimal(str(fx_price))

        # 현금 KRW 환산 합계
        cash_krw = Decimal("0")
        cash_positions = []
        for currency, amount in cash_by_currency.items():
            if currency == "KRW":
                cash_krw += amount
                cash_positions.append({"currency": currency, "amount": float(amount), "amount_krw": float(amount)})
            else:
                converted = amount * fx_rate
                cash_krw += converted
                cash_positions.append({"currency": currency, "amount": float(amount), "amount_krw": float(converted)})

        # 보유종목 평가액 (통화별 KRW 환산)
        holdings_value_krw = Decimal("0")
        for h in holdings:
            value = Decimal(str(h.get("value", 0)))
            if h.get("currency", "KRW") != "KRW":
                value_krw = value * fx_rate
            else:
                value_krw = value
            h["value_krw"] = float(value_krw)
            holdings_value_krw += value_krw

        result["cash_balance"] = float(cash_krw)
        result["cash_positions"] = cash_positions  # 통화별 현금 상세
        result["holdings"] = holdings
        result["balance"] = float(cash_krw + holdings_value_krw)

    return result
