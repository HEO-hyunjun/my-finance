"""Phase 2 스키마/도메인 개편 테스트.

- get_asset_breakdown 도메인 매핑 (cash/deposit/equity_kr, 부채 제외)
- Account 상품속성 검증 (monthly_amount는 savings에만)
- AccountType에 loan/credit_card 존재
- EntryCreate dividend/fee 부호 정규화
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.account import Account, AccountType
from app.models.entry import EntryType
from app.models.security import AssetClass, DataSource, Security, SecurityPrice
from app.schemas.account import AccountCreate, AccountUpdate
from app.schemas.entry import EntryCreate
from app.services.entry_service import create_entry, create_trade
from app.services.portfolio_v2_service import get_asset_breakdown, get_total_assets


async def test_asset_breakdown_domain_mapping(db):
    user_id = uuid.uuid4()
    cash = Account(user_id=user_id, account_type=AccountType.CASH, name="현금", currency="KRW")
    parking = Account(user_id=user_id, account_type=AccountType.PARKING, name="파킹", currency="KRW")
    deposit = Account(user_id=user_id, account_type=AccountType.DEPOSIT, name="예금", currency="KRW")
    savings = Account(user_id=user_id, account_type=AccountType.SAVINGS, name="적금", currency="KRW")
    loan = Account(user_id=user_id, account_type=AccountType.LOAN, name="대출", currency="KRW")
    inv = Account(user_id=user_id, account_type=AccountType.INVESTMENT, name="증권", currency="KRW")
    sec = Security(
        symbol="005930", name="삼성전자", currency="KRW",
        asset_class=AssetClass.EQUITY_KR, data_source=DataSource.YAHOO,
    )
    db.add_all([cash, parking, deposit, savings, loan, inv, sec])
    await db.flush()
    db.add(SecurityPrice(
        security_id=sec.id, price_date=date(2026, 7, 1),
        close_price=Decimal("60000"), currency="KRW",
    ))
    await db.flush()

    now = datetime.now(timezone.utc)
    for acc, amt in [
        (cash, "1000000"), (parking, "500000"),
        (deposit, "2000000"), (savings, "300000"), (inv, "1000000"),
    ]:
        await create_entry(db, user_id, account_id=acc.id, type=EntryType.INCOME,
                           amount=Decimal(amt), currency="KRW", transacted_at=now)
    # 부채: 음수 잔액
    await create_entry(db, user_id, account_id=loan.id, type=EntryType.EXPENSE,
                       amount=Decimal("-5000000"), currency="KRW", transacted_at=now)
    # 투자: 10주 매수 @ 50000 → 현금 500000 남음, 평가액 10*60000=600000
    await create_trade(db, user_id, account_id=inv.id, security_id=sec.id,
                       trade_type=EntryType.BUY, quantity=Decimal("10"),
                       unit_price=Decimal("50000"))

    breakdown = await get_asset_breakdown(db, user_id)

    # cash = 현금 1,000,000 + 파킹 500,000 + 투자현금 500,000 = 2,000,000
    assert breakdown["cash"] == 2000000.0
    # deposit = 예금 2,000,000 + 적금 300,000 = 2,300,000
    assert breakdown["deposit"] == 2300000.0
    # equity_kr = 10주 × 60,000 = 600,000
    assert breakdown["equity_kr"] == 600000.0
    # 부채는 breakdown에서 제외
    assert "loan" not in breakdown
    assert all(v > 0 for v in breakdown.values())


async def test_asset_breakdown_investment_usd_cash(db):
    """KRW 투자계좌가 보유한 USD 현금도 cash 버킷에 환산 합산된다."""
    user_id = uuid.uuid4()
    inv = Account(user_id=user_id, account_type=AccountType.INVESTMENT, name="증권", currency="KRW")
    fx = Security(
        symbol="USDKRW=X", name="달러원", currency="KRW",
        asset_class=AssetClass.CURRENCY_PAIR, data_source=DataSource.YAHOO,
    )
    db.add_all([inv, fx])
    await db.flush()
    db.add(SecurityPrice(
        security_id=fx.id, price_date=date(2026, 7, 1),
        close_price=Decimal("1380"), currency="KRW",
    ))
    await db.flush()

    now = datetime.now(timezone.utc)
    await create_entry(db, user_id, account_id=inv.id, type=EntryType.INCOME,
                       amount=Decimal("1000000"), currency="KRW", transacted_at=now)
    await create_entry(db, user_id, account_id=inv.id, type=EntryType.INCOME,
                       amount=Decimal("500"), currency="USD", transacted_at=now)

    breakdown = await get_asset_breakdown(db, user_id)
    # cash = 1,000,000 KRW + 500 USD × 1380 = 1,690,000
    assert breakdown["cash"] == 1690000.0


async def test_total_assets_net_worth_debt(db):
    """부채 계좌는 net_worth = 자산 − 부채, debt는 양수로 노출."""
    user_id = uuid.uuid4()
    cash = Account(user_id=user_id, account_type=AccountType.CASH, name="현금", currency="KRW")
    loan = Account(user_id=user_id, account_type=AccountType.LOAN, name="대출", currency="KRW")
    db.add_all([cash, loan])
    await db.flush()

    now = datetime.now(timezone.utc)
    await create_entry(db, user_id, account_id=cash.id, type=EntryType.INCOME,
                       amount=Decimal("1000000"), currency="KRW", transacted_at=now)
    await create_entry(db, user_id, account_id=loan.id, type=EntryType.EXPENSE,
                       amount=Decimal("-300000"), currency="KRW", transacted_at=now)

    result = await get_total_assets(db, user_id)
    assert result["net_worth_krw"] == Decimal("700000")
    assert result["total_debt_krw"] == Decimal("300000")
    assert result["total_assets_krw"] == Decimal("1000000")


def test_account_create_monthly_amount_only_savings():
    # 적금이면 허용
    AccountCreate(account_type="savings", name="적금", monthly_amount=Decimal("100000"))
    # 적금이 아니면 거부
    with pytest.raises(ValidationError):
        AccountCreate(account_type="deposit", name="예금", monthly_amount=Decimal("100000"))


def test_account_update_monthly_amount_guard():
    # account_type이 함께 오고 savings가 아니면 거부
    with pytest.raises(ValidationError):
        AccountUpdate(account_type="cash", monthly_amount=Decimal("50000"))
    # savings면 허용
    AccountUpdate(account_type="savings", monthly_amount=Decimal("50000"))


def test_account_type_has_liability_members():
    assert AccountType.LOAN.value == "loan"
    assert AccountType.CREDIT_CARD.value == "credit_card"


def test_entry_create_dividend_fee_sign():
    common = dict(account_id=uuid.uuid4(), currency="KRW", transacted_at=datetime.now(timezone.utc))
    # 배당은 양수로 정규화
    dividend = EntryCreate(type="dividend", amount=Decimal("-5000"), **common)
    assert dividend.amount == Decimal("5000")
    # 수수료는 음수로 정규화
    fee = EntryCreate(type="fee", amount=Decimal("3000"), **common)
    assert fee.amount == Decimal("-3000")
