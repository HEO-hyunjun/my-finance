"""잔액/보유수량에 영향을 주는 모든 경로의 엣지케이스 테스트"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app.models.account import Account, AccountType
from app.models.security import Security, AssetClass, DataSource
from app.services.entry_service import (
    create_entry,
    create_transfer,
    create_trade,
    adjust_balance,
    get_account_balance,
    get_holding_quantity,
)
from app.models.entry import EntryType


async def _setup_cash(db):
    user_id = uuid.uuid4()
    acc = Account(user_id=user_id, account_type=AccountType.CASH, name="테스트통장", currency="KRW")
    db.add(acc)
    await db.flush()
    return user_id, acc


async def _setup_investment(db):
    user_id = uuid.uuid4()
    acc = Account(user_id=user_id, account_type=AccountType.INVESTMENT, name="증권계좌", currency="KRW")
    sec = Security(
        symbol="005930.KS", name="삼성전자", currency="KRW",
        asset_class=AssetClass.EQUITY_KR, data_source=DataSource.YAHOO,
    )
    db.add_all([acc, sec])
    await db.flush()
    return user_id, acc, sec


async def _setup_two_accounts(db):
    user_id = uuid.uuid4()
    src = Account(user_id=user_id, account_type=AccountType.CASH, name="급여통장", currency="KRW")
    dst = Account(user_id=user_id, account_type=AccountType.PARKING, name="파킹통장", currency="KRW")
    db.add_all([src, dst])
    await db.flush()
    return user_id, src, dst


# ═══ 기본 입출금 ═══


async def test_income_increases_balance(db):
    """INCOME 엔트리가 잔액을 증가시킨다"""
    user_id, acc = await _setup_cash(db)
    await create_entry(db, user_id, account_id=acc.id, type=EntryType.INCOME,
                       amount=Decimal("5000000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))
    balance = await get_account_balance(db, acc.id)
    assert balance == Decimal("5000000")


async def test_expense_decreases_balance(db):
    """EXPENSE 엔트리가 잔액을 감소시킨다"""
    user_id, acc = await _setup_cash(db)
    await create_entry(db, user_id, account_id=acc.id, type=EntryType.INCOME,
                       amount=Decimal("5000000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))
    await create_entry(db, user_id, account_id=acc.id, type=EntryType.EXPENSE,
                       amount=Decimal("-100000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))
    balance = await get_account_balance(db, acc.id)
    assert balance == Decimal("4900000")


async def test_negative_balance_allowed(db):
    """잔액이 음수가 되는 것이 허용된다 (제약 없음)"""
    user_id, acc = await _setup_cash(db)
    await create_entry(db, user_id, account_id=acc.id, type=EntryType.EXPENSE,
                       amount=Decimal("-100000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))
    balance = await get_account_balance(db, acc.id)
    assert balance == Decimal("-100000")


# ═══ 이체 (Transfer) ═══


async def test_transfer_zero_sum(db):
    """이체 후 전체 합계는 보존된다 (출금 + 입금 = 0)"""
    user_id, src, dst = await _setup_two_accounts(db)
    await create_entry(db, user_id, account_id=src.id, type=EntryType.INCOME,
                       amount=Decimal("1000000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))

    await create_transfer(db, user_id,
                          source_account_id=src.id, target_account_id=dst.id,
                          amount=Decimal("300000"), currency="KRW",
                          transacted_at=datetime.now(timezone.utc))

    src_bal = await get_account_balance(db, src.id)
    dst_bal = await get_account_balance(db, dst.id)
    assert src_bal == Decimal("700000")
    assert dst_bal == Decimal("300000")
    assert src_bal + dst_bal == Decimal("1000000")


async def test_multiple_transfers_consistency(db):
    """연속 이체 후에도 전체 합계가 보존된다"""
    user_id, src, dst = await _setup_two_accounts(db)
    await create_entry(db, user_id, account_id=src.id, type=EntryType.INCOME,
                       amount=Decimal("1000000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))

    for _ in range(5):
        await create_transfer(db, user_id,
                              source_account_id=src.id, target_account_id=dst.id,
                              amount=Decimal("100000"), currency="KRW",
                              transacted_at=datetime.now(timezone.utc))

    src_bal = await get_account_balance(db, src.id)
    dst_bal = await get_account_balance(db, dst.id)
    assert src_bal == Decimal("500000")
    assert dst_bal == Decimal("500000")


# ═══ 주식 매매 (Trade) ═══


async def test_buy_deducts_cash_adds_quantity(db):
    """BUY: 현금 차감 + 보유수량 증가"""
    user_id, acc, sec = await _setup_investment(db)
    await create_entry(db, user_id, account_id=acc.id, type=EntryType.INCOME,
                       amount=Decimal("10000000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))

    await create_trade(db, user_id, account_id=acc.id, security_id=sec.id,
                       trade_type="buy", quantity=Decimal("10"),
                       unit_price=Decimal("70000"), fee=Decimal("1000"),
                       currency="KRW", transacted_at=datetime.now(timezone.utc))

    balance = await get_account_balance(db, acc.id)
    qty = await get_holding_quantity(db, acc.id, sec.id)
    # 10,000,000 - (10 * 70,000 + 1,000) = 9,299,000
    assert balance == Decimal("9299000")
    assert qty == Decimal("10")


async def test_sell_adds_cash_reduces_quantity(db):
    """SELL: 현금 증가 + 보유수량 감소"""
    user_id, acc, sec = await _setup_investment(db)
    await create_entry(db, user_id, account_id=acc.id, type=EntryType.INCOME,
                       amount=Decimal("10000000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))

    await create_trade(db, user_id, account_id=acc.id, security_id=sec.id,
                       trade_type="buy", quantity=Decimal("10"),
                       unit_price=Decimal("70000"), fee=Decimal("0"),
                       currency="KRW", transacted_at=datetime.now(timezone.utc))

    await create_trade(db, user_id, account_id=acc.id, security_id=sec.id,
                       trade_type="sell", quantity=Decimal("5"),
                       unit_price=Decimal("80000"), fee=Decimal("500"),
                       currency="KRW", transacted_at=datetime.now(timezone.utc))

    balance = await get_account_balance(db, acc.id)
    qty = await get_holding_quantity(db, acc.id, sec.id)
    # SELL amount = qty * price (fee는 fee 필드에만 기록, amount에 미반영)
    # 10M - 700000 + (5*80000) = 9,700,000
    assert balance == Decimal("9700000")
    assert qty == Decimal("5")


async def test_buy_fee_correctly_deducted(db):
    """매수 시 수수료가 현금에서 정확히 차감된다"""
    user_id, acc, sec = await _setup_investment(db)
    await create_entry(db, user_id, account_id=acc.id, type=EntryType.INCOME,
                       amount=Decimal("1000000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))

    await create_trade(db, user_id, account_id=acc.id, security_id=sec.id,
                       trade_type="buy", quantity=Decimal("1"),
                       unit_price=Decimal("100000"), fee=Decimal("150"),
                       currency="KRW", transacted_at=datetime.now(timezone.utc))

    balance = await get_account_balance(db, acc.id)
    # 1,000,000 - (100,000 + 150) = 899,850
    assert balance == Decimal("899850")


async def test_sell_all_quantity_becomes_zero(db):
    """전량 매도 시 보유수량이 정확히 0이 된다"""
    user_id, acc, sec = await _setup_investment(db)
    await create_entry(db, user_id, account_id=acc.id, type=EntryType.INCOME,
                       amount=Decimal("10000000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))

    await create_trade(db, user_id, account_id=acc.id, security_id=sec.id,
                       trade_type="buy", quantity=Decimal("10"),
                       unit_price=Decimal("50000"), fee=Decimal("0"),
                       currency="KRW", transacted_at=datetime.now(timezone.utc))

    await create_trade(db, user_id, account_id=acc.id, security_id=sec.id,
                       trade_type="sell", quantity=Decimal("10"),
                       unit_price=Decimal("55000"), fee=Decimal("0"),
                       currency="KRW", transacted_at=datetime.now(timezone.utc))

    qty = await get_holding_quantity(db, acc.id, sec.id)
    balance = await get_account_balance(db, acc.id)
    assert qty == Decimal("0")
    # 10M - 500000 + 550000 = 10,050,000
    assert balance == Decimal("10050000")


# ═══ 엔트리 수정 (Update) ═══


async def test_update_entry_amount_affects_balance(db):
    """엔트리 금액 수정 시 잔액이 정확히 반영된다"""
    user_id, acc = await _setup_cash(db)
    entry = await create_entry(db, user_id, account_id=acc.id, type=EntryType.INCOME,
                               amount=Decimal("100000"), currency="KRW",
                               transacted_at=datetime.now(timezone.utc))

    assert await get_account_balance(db, acc.id) == Decimal("100000")

    entry.amount = Decimal("150000")
    await db.flush()

    assert await get_account_balance(db, acc.id) == Decimal("150000")


async def test_delete_entry_reverses_balance(db):
    """엔트리 삭제 시 잔액이 원래대로 돌아간다"""
    user_id, acc = await _setup_cash(db)
    await create_entry(db, user_id, account_id=acc.id, type=EntryType.INCOME,
                       amount=Decimal("500000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))
    entry = await create_entry(db, user_id, account_id=acc.id, type=EntryType.EXPENSE,
                               amount=Decimal("-200000"), currency="KRW",
                               transacted_at=datetime.now(timezone.utc))

    assert await get_account_balance(db, acc.id) == Decimal("300000")

    await db.delete(entry)
    await db.flush()

    assert await get_account_balance(db, acc.id) == Decimal("500000")


# ═══ 잔액 보정 (Adjustment) ═══


async def test_adjust_balance_creates_diff_entry(db):
    """보정 시 현재 잔액과 목표 잔액의 차이만큼 엔트리가 생성된다"""
    user_id, acc = await _setup_cash(db)
    await create_entry(db, user_id, account_id=acc.id, type=EntryType.INCOME,
                       amount=Decimal("300000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))

    await adjust_balance(db, user_id, account_id=acc.id,
                         target_balance=Decimal("500000"), currency="KRW")

    balance = await get_account_balance(db, acc.id)
    assert balance == Decimal("500000")


async def test_adjust_balance_downward(db):
    """잔액을 하향 보정"""
    user_id, acc = await _setup_cash(db)
    await create_entry(db, user_id, account_id=acc.id, type=EntryType.INCOME,
                       amount=Decimal("1000000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))

    await adjust_balance(db, user_id, account_id=acc.id,
                         target_balance=Decimal("800000"), currency="KRW")

    balance = await get_account_balance(db, acc.id)
    assert balance == Decimal("800000")


async def test_adjust_to_zero(db):
    """잔액을 0으로 보정"""
    user_id, acc = await _setup_cash(db)
    await create_entry(db, user_id, account_id=acc.id, type=EntryType.INCOME,
                       amount=Decimal("100000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))

    await adjust_balance(db, user_id, account_id=acc.id,
                         target_balance=Decimal("0"), currency="KRW")

    balance = await get_account_balance(db, acc.id)
    assert balance == Decimal("0")


# ═══ 이자 (Interest/Dividend) ═══


async def test_interest_entry_adds_to_balance(db):
    """INTEREST 엔트리가 잔액에 정상 반영된다"""
    user_id = uuid.uuid4()
    acc = Account(user_id=user_id, account_type=AccountType.PARKING, name="파킹통장",
                  currency="KRW", interest_rate=Decimal("2.0"))
    db.add(acc)
    await db.flush()

    await create_entry(db, user_id, account_id=acc.id, type=EntryType.INCOME,
                       amount=Decimal("10000000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))

    await create_entry(db, user_id, account_id=acc.id, type=EntryType.INTEREST,
                       amount=Decimal("462.74"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))

    balance = await get_account_balance(db, acc.id)
    assert balance == Decimal("10000462.74")


async def test_dividend_adds_to_balance(db):
    """DIVIDEND 엔트리가 잔액에 정상 반영된다"""
    user_id, acc, sec = await _setup_investment(db)
    await create_entry(db, user_id, account_id=acc.id, type=EntryType.INCOME,
                       amount=Decimal("5000000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))

    await create_entry(db, user_id, account_id=acc.id, type=EntryType.DIVIDEND,
                       amount=Decimal("50000"), currency="KRW",
                       transacted_at=datetime.now(timezone.utc))

    balance = await get_account_balance(db, acc.id)
    assert balance == Decimal("5050000")


# ═══ 복합 시나리오 ═══


async def test_mixed_operations_final_balance(db):
    """입금 → 이체 → 매수 → 매도 → 이자 → 지출 후 최종 잔액 정확성"""
    user_id = uuid.uuid4()
    cash = Account(user_id=user_id, account_type=AccountType.CASH, name="급여통장", currency="KRW")
    inv = Account(user_id=user_id, account_type=AccountType.INVESTMENT, name="증권", currency="KRW")
    sec = Security(symbol="AAPL", name="Apple", currency="USD",
                   asset_class=AssetClass.EQUITY_US, data_source=DataSource.YAHOO)
    db.add_all([cash, inv, sec])
    await db.flush()
    now = datetime.now(timezone.utc)

    # 1. 월급 입금 500만
    await create_entry(db, user_id, account_id=cash.id, type=EntryType.INCOME,
                       amount=Decimal("5000000"), currency="KRW", transacted_at=now)

    # 2. 증권계좌로 이체 200만
    await create_transfer(db, user_id,
                          source_account_id=cash.id, target_account_id=inv.id,
                          amount=Decimal("2000000"), currency="KRW", transacted_at=now)

    # 3. 주식 매수 10주 × 15만 + 수수료 500
    await create_trade(db, user_id, account_id=inv.id, security_id=sec.id,
                       trade_type="buy", quantity=Decimal("10"),
                       unit_price=Decimal("150000"), fee=Decimal("500"),
                       currency="KRW", transacted_at=now)

    # 4. 5주 매도 × 16만 - 수수료 300
    await create_trade(db, user_id, account_id=inv.id, security_id=sec.id,
                       trade_type="sell", quantity=Decimal("5"),
                       unit_price=Decimal("160000"), fee=Decimal("300"),
                       currency="KRW", transacted_at=now)

    # 5. 이자 수령
    await create_entry(db, user_id, account_id=cash.id, type=EntryType.INTEREST,
                       amount=Decimal("1000"), currency="KRW", transacted_at=now)

    # 6. 월세 지출 50만
    await create_entry(db, user_id, account_id=cash.id, type=EntryType.EXPENSE,
                       amount=Decimal("-500000"), currency="KRW", transacted_at=now)

    cash_bal = await get_account_balance(db, cash.id)
    inv_bal = await get_account_balance(db, inv.id)
    inv_qty = await get_holding_quantity(db, inv.id, sec.id)

    # 급여통장: 5M - 2M + 1000 - 500000 = 2,501,000
    assert cash_bal == Decimal("2501000")

    # 증권계좌: 2M - (10*150000+500)(매수) + (5*160000)(매도, fee는 amount 미반영)
    #         = 2M - 1,500,500 + 800,000 = 1,299,500
    assert inv_bal == Decimal("1299500")

    # 보유수량: 10 - 5 = 5주
    assert inv_qty == Decimal("5")

    # 전체 현금 합계
    total_cash = cash_bal + inv_bal
    assert total_cash == Decimal("3800500")
