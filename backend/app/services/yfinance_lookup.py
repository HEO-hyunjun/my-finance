"""yfinance 기반 종목 검색/조회 — 외부 API 호출만 담당.

DB 접근은 하지 않는다. 호출자(security_service)가 결합한다.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from decimal import Decimal

import yfinance as yf

from app.models.security import AssetClass


_KR_EXCHANGES = {"KSC", "KOSDAQ", "KRX", "KOE"}


def _classify_asset(quote_type: str | None, exchange: str | None) -> AssetClass:
    qt = (quote_type or "").upper()
    ex = (exchange or "").upper()
    if qt == "CURRENCY":
        return AssetClass.CURRENCY_PAIR
    if qt in {"FUTURE", "COMMODITY"}:
        return AssetClass.COMMODITY
    if ex in _KR_EXCHANGES:
        return AssetClass.EQUITY_KR
    return AssetClass.EQUITY_US


def _infer_currency(exchange: str | None, fallback: str | None = None) -> str:
    ex = (exchange or "").upper()
    if ex in _KR_EXCHANGES:
        return "KRW"
    if ex in {"TYO", "JPX"}:
        return "JPY"
    if ex == "LSE":
        return "GBP"
    return (fallback or "USD")[:3].upper()


@dataclass
class YfQuote:
    symbol: str
    name: str
    currency: str
    exchange: str | None
    asset_class: AssetClass


def _search_sync(query: str, max_results: int) -> list[YfQuote]:
    if not query.strip():
        return []
    res = yf.Search(query, max_results=max_results, news_count=0, lists_count=0)
    out: list[YfQuote] = []
    for q in (res.quotes or []):
        symbol = q.get("symbol")
        if not symbol:
            continue
        name = q.get("longname") or q.get("shortname") or symbol
        exchange = q.get("exchange") or q.get("exchDisp")
        quote_type = q.get("quoteType") or q.get("typeDisp")
        out.append(
            YfQuote(
                symbol=symbol,
                name=name[:100],
                currency=_infer_currency(exchange),
                exchange=(exchange[:20] if exchange else None),
                asset_class=_classify_asset(quote_type, exchange),
            )
        )
    return out


async def search_quotes(query: str, max_results: int = 20) -> list[YfQuote]:
    return await asyncio.to_thread(_search_sync, query, max_results)


def _read_fast_info(info, key: str):
    if info is None:
        return None
    if isinstance(info, dict):
        return info.get(key)
    return getattr(info, key, None)


def _ticker_meta_sync(symbol: str) -> YfQuote | None:
    try:
        t = yf.Ticker(symbol)
        info = getattr(t, "fast_info", None)
        currency = _read_fast_info(info, "currency")
        exchange = _read_fast_info(info, "exchange")
        name = symbol
        quote_type = None
        if not currency or not exchange:
            try:
                full = t.info or {}
                currency = currency or full.get("currency")
                exchange = exchange or full.get("exchange")
                name = full.get("longName") or full.get("shortName") or symbol
                quote_type = full.get("quoteType")
            except Exception:
                pass
        if not currency and not exchange and name == symbol:
            return None
        return YfQuote(
            symbol=symbol,
            name=(name or symbol)[:100],
            currency=(currency or _infer_currency(exchange))[:3].upper(),
            exchange=(exchange[:20] if exchange else None),
            asset_class=_classify_asset(quote_type, exchange),
        )
    except Exception:
        return None


async def get_ticker_meta(symbol: str) -> YfQuote | None:
    return await asyncio.to_thread(_ticker_meta_sync, symbol)


def _last_price_sync(symbol: str) -> Decimal | None:
    try:
        t = yf.Ticker(symbol)
        info = getattr(t, "fast_info", None)
        price = _read_fast_info(info, "last_price")
        if price is None:
            hist = t.history(period="1d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
        if price is None:
            return None
        return Decimal(str(round(float(price), 4)))
    except Exception:
        return None


async def get_last_price(symbol: str) -> Decimal | None:
    return await asyncio.to_thread(_last_price_sync, symbol)
