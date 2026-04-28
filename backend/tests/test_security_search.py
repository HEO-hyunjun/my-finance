"""yfinance 기반 종목 검색/ensure 동작 테스트.

외부 yfinance API는 monkeypatch로 차단하고, DB 매칭/생성 로직만 검증한다.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.security import AssetClass, DataSource, Security
from app.services import security_service, yfinance_lookup


def _quote(
    symbol: str,
    name: str = "Test Co",
    currency: str = "USD",
    exchange: str | None = "NMS",
    asset_class: AssetClass = AssetClass.EQUITY_US,
) -> yfinance_lookup.YfQuote:
    return yfinance_lookup.YfQuote(
        symbol=symbol,
        name=name,
        currency=currency,
        exchange=exchange,
        asset_class=asset_class,
    )


@pytest.mark.asyncio
async def test_search_returns_empty_when_no_quotes(db, monkeypatch):
    async def fake_search(query, max_results=20):
        return []

    monkeypatch.setattr(yfinance_lookup, "search_quotes", fake_search)

    out = await security_service.search_securities(db, "ZZZZZ")
    assert out == []


@pytest.mark.asyncio
async def test_search_marks_unknown_id_as_none(db, monkeypatch):
    async def fake_search(query, max_results=20):
        return [_quote("MSFT", "Microsoft Corporation")]

    monkeypatch.setattr(yfinance_lookup, "search_quotes", fake_search)

    out = await security_service.search_securities(db, "MSFT")
    assert len(out) == 1
    hit = out[0]
    assert hit.symbol == "MSFT"
    assert hit.name == "Microsoft Corporation"
    assert hit.currency == "USD"
    assert hit.asset_class == AssetClass.EQUITY_US.value
    assert hit.id is None


@pytest.mark.asyncio
async def test_search_fills_id_when_db_has_symbol(db, monkeypatch):
    existing = Security(
        symbol="MSFT",
        name="Microsoft Corporation",
        currency="USD",
        asset_class=AssetClass.EQUITY_US,
        data_source=DataSource.YAHOO,
        exchange="NMS",
    )
    db.add(existing)
    await db.commit()
    await db.refresh(existing)

    async def fake_search(query, max_results=20):
        return [_quote("MSFT")]

    monkeypatch.setattr(yfinance_lookup, "search_quotes", fake_search)

    out = await security_service.search_securities(db, "MSFT")
    assert len(out) == 1
    assert out[0].id == existing.id
    assert out[0].name == "Microsoft Corporation"


@pytest.mark.asyncio
async def test_ensure_creates_when_missing(db, monkeypatch):
    async def fake_meta(symbol):
        return _quote(symbol, "Microsoft Corporation")

    async def fake_price(symbol):
        return Decimal("417.96")

    monkeypatch.setattr(yfinance_lookup, "get_ticker_meta", fake_meta)
    monkeypatch.setattr(yfinance_lookup, "get_last_price", fake_price)

    result = await security_service.ensure_security_by_symbol(db, "msft")
    assert result.security.symbol == "MSFT"
    assert result.security.currency == "USD"
    assert result.current_price == Decimal("417.96")

    rows = (
        await db.execute(select(Security).where(Security.symbol == "MSFT"))
    ).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_ensure_returns_existing_without_recreating(db, monkeypatch):
    existing = Security(
        symbol="AAPL",
        name="Apple Inc.",
        currency="USD",
        asset_class=AssetClass.EQUITY_US,
        data_source=DataSource.YAHOO,
        exchange="NMS",
    )
    db.add(existing)
    await db.commit()
    await db.refresh(existing)

    meta_calls = {"count": 0}

    async def fake_meta(symbol):
        meta_calls["count"] += 1
        return _quote(symbol)

    async def fake_price(symbol):
        return Decimal("190.50")

    monkeypatch.setattr(yfinance_lookup, "get_ticker_meta", fake_meta)
    monkeypatch.setattr(yfinance_lookup, "get_last_price", fake_price)

    result = await security_service.ensure_security_by_symbol(db, "AAPL")
    assert result.security.id == existing.id
    assert result.current_price == Decimal("190.50")
    assert meta_calls["count"] == 0


@pytest.mark.asyncio
async def test_ensure_raises_when_symbol_not_found(db, monkeypatch):
    from fastapi import HTTPException

    async def fake_meta(symbol):
        return None

    async def fake_price(symbol):
        return None

    monkeypatch.setattr(yfinance_lookup, "get_ticker_meta", fake_meta)
    monkeypatch.setattr(yfinance_lookup, "get_last_price", fake_price)

    with pytest.raises(HTTPException) as exc:
        await security_service.ensure_security_by_symbol(db, "NOPE_INVALID")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_ensure_rejects_blank_symbol(db):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await security_service.ensure_security_by_symbol(db, "   ")
    assert exc.value.status_code == 400


def test_classify_asset_currency_pair():
    assert yfinance_lookup._classify_asset("CURRENCY", "CCY") == AssetClass.CURRENCY_PAIR


def test_classify_asset_kr_equity():
    assert yfinance_lookup._classify_asset("EQUITY", "KSC") == AssetClass.EQUITY_KR


def test_classify_asset_us_equity_default():
    assert yfinance_lookup._classify_asset("EQUITY", "NMS") == AssetClass.EQUITY_US


def test_classify_asset_commodity():
    assert yfinance_lookup._classify_asset("FUTURE", "CME") == AssetClass.COMMODITY


def test_infer_currency_kr():
    assert yfinance_lookup._infer_currency("KSC") == "KRW"


def test_infer_currency_jp():
    assert yfinance_lookup._infer_currency("TYO") == "JPY"


def test_infer_currency_default_usd():
    assert yfinance_lookup._infer_currency(None) == "USD"
