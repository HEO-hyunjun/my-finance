import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType
from app.services.entry_service import get_account_balance, get_account_cash_balance, get_holdings


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
        cash_balance = await get_account_cash_balance(db, account_id)
        holdings = await get_holdings(db, account_id)
        holdings_value = sum(h.get("value", 0) for h in holdings)
        result["cash_balance"] = cash_balance
        result["holdings"] = holdings
        result["balance"] = cash_balance + holdings_value  # 현금 + 평가액

    return result
