import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security import DataSource, Security, SecurityPrice
from app.services import yfinance_lookup


@dataclass
class SecuritySearchHit:
    """검색 결과 한 줄 (yfinance 메타 + DB id 매칭 여부)"""

    symbol: str
    name: str
    currency: str
    exchange: str | None
    asset_class: str
    id: uuid.UUID | None


@dataclass
class EnsureResult:
    security: Security
    current_price: Decimal | None


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


async def search_securities(
    db: AsyncSession, query: str, max_results: int = 20
) -> list[SecuritySearchHit]:
    """yfinance에서 검색하고, 같은 symbol이 DB에 있으면 id를 채워 반환"""
    quotes = await yfinance_lookup.search_quotes(query, max_results=max_results)
    if not quotes:
        return []
    symbols = [q.symbol for q in quotes]
    stmt = select(Security).where(Security.symbol.in_(symbols))
    existing = {s.symbol: s for s in (await db.execute(stmt)).scalars().all()}
    hits: list[SecuritySearchHit] = []
    for q in quotes:
        row = existing.get(q.symbol)
        hits.append(
            SecuritySearchHit(
                symbol=q.symbol,
                name=row.name if row else q.name,
                currency=row.currency if row else q.currency,
                exchange=row.exchange if row else q.exchange,
                asset_class=(row.asset_class.value if row else q.asset_class.value),
                id=row.id if row else None,
            )
        )
    return hits


async def ensure_security_by_symbol(
    db: AsyncSession, symbol: str
) -> EnsureResult:
    """심볼로 Security를 보장한다. 없으면 yfinance 메타로 생성. 현재가도 함께 조회."""
    symbol = symbol.strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="symbol이 필요합니다")

    row = await get_security_by_symbol(db, symbol)
    if row is None:
        meta = await yfinance_lookup.get_ticker_meta(symbol)
        if meta is None:
            raise HTTPException(
                status_code=404, detail=f"종목을 찾을 수 없습니다: {symbol}"
            )
        row = Security(
            symbol=meta.symbol,
            name=meta.name,
            currency=meta.currency,
            asset_class=meta.asset_class,
            data_source=DataSource.YAHOO,
            exchange=meta.exchange,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)

    price = await yfinance_lookup.get_last_price(row.symbol)
    return EnsureResult(security=row, current_price=price)


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
