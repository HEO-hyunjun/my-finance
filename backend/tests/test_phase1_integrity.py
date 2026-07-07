"""Phase 1 정합성 버그픽스 테스트.

- 이체/매매 그룹 무결성 (단독 다리 수정 409, 그룹 삭제 시 양다리 소멸)
- 크로스통화 이체
- 통화 구분 잔액
- 과매도 거부
- 월이자 자기치유 델타 idempotency
- fee-inclusive 평균단가
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.api.deps import get_current_user
from app.main import app
from app.models.account import Account, AccountType
from app.models.entry import Entry, EntryType
from app.models.security import AssetClass, DataSource, Security
from app.models.user import User
from app.services.entry_service import (
    create_entry,
    create_transfer,
    create_trade,
    delete_entry_group,
    get_account_balance,
    get_holding_quantity,
    get_holdings,
    update_transfer_group,
    update_trade_group,
)
from app.services.interest_service import calculate_ledger_accrued_interest


async def _cash(db, currency="KRW"):
    user_id = uuid.uuid4()
    acc = Account(user_id=user_id, account_type=AccountType.CASH, name="통장", currency=currency)
    db.add(acc)
    await db.flush()
    return user_id, acc


async def _security(db, symbol="005930", currency="KRW"):
    sec = Security(
        symbol=symbol, name="종목", currency=currency,
        asset_class=AssetClass.EQUITY_KR, data_source=DataSource.YAHOO,
    )
    db.add(sec)
    await db.flush()
    return sec


# ═══ 통화 구분 잔액 ═══


async def test_currency_scoped_balance(db):
    user_id, acc = await _cash(db)
    await create_entry(db, user_id, account_id=acc.id, type=EntryType.INCOME,
                       amount=Decimal("1000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))
    await create_entry(db, user_id, account_id=acc.id, type=EntryType.INCOME,
                       amount=Decimal("500"), currency="USD",
                       transacted_at=datetime.now(timezone.utc))

    assert await get_account_balance(db, acc.id, "KRW") == Decimal("1000")
    assert await get_account_balance(db, acc.id, "USD") == Decimal("500")
    # 필터 없으면 통화 무시 전체 합
    assert await get_account_balance(db, acc.id) == Decimal("1500")


# ═══ 크로스통화 이체 ═══


async def test_cross_currency_transfer_legs(db):
    user_id = uuid.uuid4()
    src = Account(user_id=user_id, account_type=AccountType.CASH, name="원화", currency="KRW")
    tgt = Account(user_id=user_id, account_type=AccountType.INVESTMENT, name="달러", currency="USD")
    db.add_all([src, tgt])
    await db.flush()

    group = await create_transfer(
        db, user_id,
        source_account_id=src.id, target_account_id=tgt.id,
        amount=Decimal("1380000"), currency="KRW",
        target_currency="USD", target_amount=Decimal("1000"),
        exchange_rate=Decimal("1380"),
    )

    entries = (await db.execute(
        select(Entry).where(Entry.entry_group_id == group.id)
    )).scalars().all()
    out = next(e for e in entries if e.type == EntryType.TRANSFER_OUT)
    inn = next(e for e in entries if e.type == EntryType.TRANSFER_IN)

    assert out.currency == "KRW"
    assert out.amount == Decimal("-1380000")
    assert out.exchange_rate == Decimal("1380")
    assert inn.currency == "USD"
    assert inn.amount == Decimal("1000")
    assert inn.exchange_rate == Decimal("1380")


async def test_cross_currency_transfer_requires_target_amount(db):
    user_id = uuid.uuid4()
    src = Account(user_id=user_id, account_type=AccountType.CASH, name="원화", currency="KRW")
    tgt = Account(user_id=user_id, account_type=AccountType.INVESTMENT, name="달러", currency="USD")
    db.add_all([src, tgt])
    await db.flush()

    with pytest.raises(Exception):
        await create_transfer(
            db, user_id,
            source_account_id=src.id, target_account_id=tgt.id,
            amount=Decimal("1380000"), currency="KRW", target_currency="USD",
        )


# ═══ 그룹 수정/삭제 무결성 ═══


async def test_update_transfer_group_updates_both_legs(db):
    user_id = uuid.uuid4()
    src = Account(user_id=user_id, account_type=AccountType.CASH, name="A", currency="KRW")
    dst = Account(user_id=user_id, account_type=AccountType.PARKING, name="B", currency="KRW")
    db.add_all([src, dst])
    await db.flush()

    group = await create_transfer(db, user_id, src.id, dst.id, Decimal("100000"))
    await update_transfer_group(db, user_id, group.id, amount=Decimal("200000"))

    assert await get_account_balance(db, src.id, "KRW") == Decimal("-200000")
    assert await get_account_balance(db, dst.id, "KRW") == Decimal("200000")


async def test_delete_entry_group_removes_both_legs(db):
    user_id = uuid.uuid4()
    src = Account(user_id=user_id, account_type=AccountType.CASH, name="A", currency="KRW")
    dst = Account(user_id=user_id, account_type=AccountType.PARKING, name="B", currency="KRW")
    db.add_all([src, dst])
    await db.flush()

    await create_entry(db, user_id, account_id=src.id, type=EntryType.INCOME,
                       amount=Decimal("500000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))
    group = await create_transfer(db, user_id, src.id, dst.id, Decimal("300000"))

    await delete_entry_group(db, user_id, group.id)

    remaining = (await db.execute(
        select(Entry).where(Entry.entry_group_id == group.id)
    )).scalars().all()
    assert remaining == []
    # 이체가 완전히 사라져 원래 잔액으로 복귀
    assert await get_account_balance(db, src.id, "KRW") == Decimal("500000")
    assert await get_account_balance(db, dst.id, "KRW") == Decimal("0")


async def test_update_trade_group_recomputes_amount(db):
    user_id = uuid.uuid4()
    acc = Account(user_id=user_id, account_type=AccountType.INVESTMENT, name="증권", currency="KRW")
    db.add(acc)
    await db.flush()
    sec = await _security(db)

    group = await create_trade(db, user_id, account_id=acc.id, security_id=sec.id,
                               trade_type=EntryType.BUY, quantity=Decimal("10"),
                               unit_price=Decimal("50000"), fee=Decimal("1000"))
    await update_trade_group(db, user_id, group.id, quantity=Decimal("5"))

    entry = (await db.execute(
        select(Entry).where(Entry.entry_group_id == group.id)
    )).scalar_one()
    # 매수 5주 × 50000 + fee 1000 = -251000
    assert entry.amount == Decimal("-251000")
    assert entry.quantity == Decimal("5")


async def test_update_trade_group_oversell_rejected(db):
    user_id = uuid.uuid4()
    acc = Account(user_id=user_id, account_type=AccountType.INVESTMENT, name="증권", currency="KRW")
    db.add(acc)
    await db.flush()
    sec = await _security(db)

    await create_trade(db, user_id, account_id=acc.id, security_id=sec.id,
                       trade_type=EntryType.BUY, quantity=Decimal("10"),
                       unit_price=Decimal("50000"))
    sell_group = await create_trade(db, user_id, account_id=acc.id, security_id=sec.id,
                                    trade_type=EntryType.SELL, quantity=Decimal("3"),
                                    unit_price=Decimal("55000"))

    # 이 그룹 제외 보유량 = 10 - 3 = ... available = 7 - (-3) = 10 → 15는 초과
    with pytest.raises(Exception):
        await update_trade_group(db, user_id, sell_group.id, quantity=Decimal("15"))

    # 10까지는 허용
    await update_trade_group(db, user_id, sell_group.id, quantity=Decimal("10"))
    assert await get_holding_quantity(db, acc.id, sec.id) == Decimal("0")


# ═══ 과매도 ═══


async def test_oversell_rejected(db):
    user_id = uuid.uuid4()
    acc = Account(user_id=user_id, account_type=AccountType.INVESTMENT, name="증권", currency="KRW")
    db.add(acc)
    await db.flush()
    sec = await _security(db)

    await create_trade(db, user_id, account_id=acc.id, security_id=sec.id,
                       trade_type=EntryType.BUY, quantity=Decimal("10"),
                       unit_price=Decimal("50000"))

    with pytest.raises(Exception):
        await create_trade(db, user_id, account_id=acc.id, security_id=sec.id,
                           trade_type=EntryType.SELL, quantity=Decimal("15"),
                           unit_price=Decimal("55000"))


# ═══ fee-inclusive 평균단가 ═══


async def test_fee_inclusive_avg_price(db):
    user_id = uuid.uuid4()
    acc = Account(user_id=user_id, account_type=AccountType.INVESTMENT, name="증권", currency="KRW")
    db.add(acc)
    await db.flush()
    sec = await _security(db)

    await create_trade(db, user_id, account_id=acc.id, security_id=sec.id,
                       trade_type=EntryType.BUY, quantity=Decimal("10"),
                       unit_price=Decimal("50000"), fee=Decimal("1000"))

    holdings = await get_holdings(db, acc.id)
    # (10*50000 + 1000) / 10 = 50100
    assert holdings[0]["avg_price"] == Decimal("50100")


# ═══ 원장 기반 발생이자 + 월이자 델타 idempotency ═══


class _Ledger:
    def __init__(self, amount, transacted_at):
        self.amount = amount
        self.transacted_at = transacted_at


def test_calculate_ledger_accrued_interest():
    as_of = date(2026, 4, 1)
    # 원금 12,000,000, 90일 경과, 연 3%, 세율 15.4%
    entries = [_Ledger(Decimal("12000000"), datetime(2026, 1, 1, tzinfo=timezone.utc))]
    accrued = calculate_ledger_accrued_interest(
        entries, annual_rate=Decimal("3.0"), tax_rate=Decimal("15.400"), as_of=as_of,
    )
    # 12,000,000 × 0.03 × 90/365 × (1-0.154) ≈ 75,097
    expected = round(12000000 * 0.03 * 90 / 365 * (1 - 0.154))
    assert accrued == Decimal(str(expected))
    assert accrued > 0


async def test_monthly_interest_delta_idempotent(monkeypatch):
    """월이자 태스크를 2번 실행해도 INTEREST entry는 1건만 생성된다."""
    from app.tasks import interest_tasks

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    class _NoDisposeEngine:
        async def dispose(self):
            pass

    fixed_today = date(2026, 4, 1)
    monkeypatch.setattr(interest_tasks, "_get_async_session",
                        lambda: (sessionmaker, _NoDisposeEngine()))
    monkeypatch.setattr(interest_tasks, "tz_today", lambda: fixed_today)

    user_id = uuid.uuid4()
    async with sessionmaker() as setup:
        acc = Account(
            user_id=user_id, account_type=AccountType.DEPOSIT, name="예금",
            currency="KRW", interest_rate=Decimal("3.0"),
            tax_rate=Decimal("15.400"),
            start_date=date(2026, 1, 1),
            maturity_date=fixed_today + timedelta(days=300),
        )
        setup.add(acc)
        await setup.flush()
        setup.add(Entry(
            user_id=user_id, account_id=acc.id, type=EntryType.INCOME,
            amount=Decimal("12000000"), currency="KRW",
            transacted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ))
        await setup.commit()
        account_id = acc.id

    first = await interest_tasks._record_deposit_interest_async()
    second = await interest_tasks._record_deposit_interest_async()

    assert first["recorded"] == 1
    assert second["recorded"] == 0

    async with sessionmaker() as check:
        interest_entries = (await check.execute(
            select(Entry).where(
                Entry.account_id == account_id,
                Entry.type == EntryType.INTEREST,
            )
        )).scalars().all()
    assert len(interest_entries) == 1

    await engine.dispose()


# ═══ 엔드포인트: 그룹 소속 entry 단독 수정/삭제 거부 (409) ═══


async def _client(db):
    user = User(id=uuid.uuid4(), email=f"{uuid.uuid4()}@t.com", hashed_password="x", name="테스트")
    db.add(user)
    await db.flush()

    async def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: user
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    return client, user


async def test_grouped_entry_single_leg_patch_rejected(db):
    client, user = await _client(db)
    try:
        src = Account(user_id=user.id, account_type=AccountType.CASH, name="A", currency="KRW")
        dst = Account(user_id=user.id, account_type=AccountType.PARKING, name="B", currency="KRW")
        db.add_all([src, dst])
        await db.flush()
        group = await create_transfer(db, user.id, src.id, dst.id, Decimal("100000"))
        await db.commit()

        leg = (await db.execute(
            select(Entry).where(Entry.entry_group_id == group.id)
        )).scalars().first()

        resp = await client.patch(f"/api/v1/entries/{leg.id}", json={"amount": "999"})
        assert resp.status_code == 409
        assert resp.json()["detail"]["entry_group_id"] == str(group.id)

        # memo만 수정은 허용
        ok = await client.patch(f"/api/v1/entries/{leg.id}", json={"memo": "메모"})
        assert ok.status_code == 200
    finally:
        app.dependency_overrides.clear()
        await client.aclose()


async def test_grouped_entry_single_leg_delete_rejected(db):
    client, user = await _client(db)
    try:
        src = Account(user_id=user.id, account_type=AccountType.CASH, name="A", currency="KRW")
        dst = Account(user_id=user.id, account_type=AccountType.PARKING, name="B", currency="KRW")
        db.add_all([src, dst])
        await db.flush()
        group = await create_transfer(db, user.id, src.id, dst.id, Decimal("100000"))
        await db.commit()

        leg = (await db.execute(
            select(Entry).where(Entry.entry_group_id == group.id)
        )).scalars().first()

        resp = await client.delete(f"/api/v1/entries/{leg.id}")
        assert resp.status_code == 409

        # 그룹 API로는 삭제 성공 + 양다리 소멸
        gone = await client.delete(f"/api/v1/entry-groups/{group.id}")
        assert gone.status_code == 204
        remaining = (await db.execute(
            select(Entry).where(Entry.entry_group_id == group.id)
        )).scalars().all()
        assert remaining == []
    finally:
        app.dependency_overrides.clear()
        await client.aclose()
