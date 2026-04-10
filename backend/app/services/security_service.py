import uuid
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security import Security, SecurityPrice


async def create_security(db: AsyncSession, data: dict) -> Security:
    security = Security(**data)
    db.add(security)
    await db.commit()
    await db.refresh(security)
    return security


async def get_securities(db: AsyncSession) -> list[Security]:
    stmt = select(Security).order_by(Security.symbol)
    return list((await db.execute(stmt)).scalars().all())


async def get_security(db: AsyncSession, security_id: uuid.UUID) -> Security:
    security = await db.get(Security, security_id)
    if not security:
        raise HTTPException(status_code=404, detail="Security not found")
    return security


async def get_security_by_symbol(db: AsyncSession, symbol: str) -> Security | None:
    stmt = select(Security).where(Security.symbol == symbol)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_latest_price(
    db: AsyncSession, security_id: uuid.UUID
) -> SecurityPrice | None:
    """최신 종가 반환 (LOCF -- Last Observation Carried Forward)"""
    stmt = (
        select(SecurityPrice)
        .where(SecurityPrice.security_id == security_id)
        .order_by(SecurityPrice.price_date.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_exchange_rate(
    db: AsyncSession,
    from_currency: str,
    to_currency: str,
    target_date: date | None = None,
) -> Decimal | None:
    """환율 조회. USDKRW=X 심볼 기반. LOCF."""
    if from_currency == to_currency:
        return Decimal("1")

    symbol = f"{from_currency}{to_currency}=X"
    sec = await get_security_by_symbol(db, symbol)
    if not sec:
        return None

    stmt = select(SecurityPrice).where(SecurityPrice.security_id == sec.id)
    if target_date:
        stmt = stmt.where(SecurityPrice.price_date <= target_date)
    stmt = stmt.order_by(SecurityPrice.price_date.desc()).limit(1)

    price = (await db.execute(stmt)).scalar_one_or_none()
    return Decimal(str(price.close_price)) if price else None


async def save_price(
    db: AsyncSession,
    security_id: uuid.UUID,
    price_date: date,
    close_price: Decimal,
    currency: str,
) -> SecurityPrice:
    """시세 저장 (upsert)"""
    stmt = select(SecurityPrice).where(
        and_(
            SecurityPrice.security_id == security_id,
            SecurityPrice.price_date == price_date,
        )
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        existing.close_price = close_price
        return existing

    price = SecurityPrice(
        security_id=security_id,
        price_date=price_date,
        close_price=close_price,
        currency=currency,
    )
    db.add(price)
    await db.flush()
    return price


async def fetch_and_save_prices(db: AsyncSession) -> dict:
    """모든 종목의 최신 시세를 Yahoo Finance에서 수집하여 저장"""
    import yfinance as yf

    securities = await get_securities(db)
    saved = 0
    errors = []

    for sec in securities:
        try:
            ticker = yf.Ticker(sec.symbol)
            hist = ticker.history(period="5d")
            if hist.empty:
                continue

            for idx, row in hist.iterrows():
                price_date = idx.date()
                close_price = Decimal(str(round(row["Close"], 4)))
                await save_price(db, sec.id, price_date, close_price, sec.currency)
                saved += 1
        except Exception as e:
            errors.append({"symbol": sec.symbol, "error": str(e)})

    await db.commit()
    return {"saved": saved, "errors": errors}
