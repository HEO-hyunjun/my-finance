"""크로스뱅크 이체 쌍 탐지 + 병합 테스트."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.account import Account, AccountType
from app.models.entry import Entry, EntryType, GroupType
from app.models.import_batch import ImportBatch, StagedEntry
from app.schemas.imports import MergeSpec
from app.services import import_service
from app.services.entry_service import create_entry, merge_transfer


async def _two_accounts(db):
    user_id = uuid.uuid4()
    a = Account(user_id=user_id, account_type=AccountType.CASH, name="A은행", currency="KRW")
    b = Account(user_id=user_id, account_type=AccountType.CASH, name="B은행", currency="KRW")
    db.add_all([a, b])
    await db.flush()
    return user_id, a, b


# ═══ merge_transfer ═══


async def test_merge_transfer_success(db):
    user_id, a, b = await _two_accounts(db)
    now = datetime(2026, 7, 10, 3, tzinfo=timezone.utc)
    out = await create_entry(db, user_id, account_id=a.id, type=EntryType.EXPENSE,
                             amount=Decimal("-50000"), currency="KRW", memo="이체출금", transacted_at=now)
    inn = await create_entry(db, user_id, account_id=b.id, type=EntryType.INCOME,
                             amount=Decimal("50000"), currency="KRW", memo="이체입금", transacted_at=now)

    group = await merge_transfer(db, user_id, out.id, inn.id)
    assert group.group_type == GroupType.TRANSFER

    legs = (await db.execute(select(Entry).where(Entry.entry_group_id == group.id))).scalars().all()
    out_leg = next(e for e in legs if e.amount < 0)
    in_leg = next(e for e in legs if e.amount > 0)
    assert out_leg.type == EntryType.TRANSFER_OUT
    assert in_leg.type == EntryType.TRANSFER_IN
    assert out_leg.category_id is None and in_leg.category_id is None


async def test_merge_transfer_same_account_rejected(db):
    user_id, a, _ = await _two_accounts(db)
    now = datetime(2026, 7, 10, 3, tzinfo=timezone.utc)
    e1 = await create_entry(db, user_id, account_id=a.id, type=EntryType.EXPENSE,
                            amount=Decimal("-50000"), currency="KRW", transacted_at=now)
    e2 = await create_entry(db, user_id, account_id=a.id, type=EntryType.INCOME,
                            amount=Decimal("50000"), currency="KRW", transacted_at=now)
    with pytest.raises(Exception):
        await merge_transfer(db, user_id, e1.id, e2.id)


async def test_merge_transfer_amount_mismatch_rejected(db):
    user_id, a, b = await _two_accounts(db)
    now = datetime(2026, 7, 10, 3, tzinfo=timezone.utc)
    e1 = await create_entry(db, user_id, account_id=a.id, type=EntryType.EXPENSE,
                            amount=Decimal("-50000"), currency="KRW", transacted_at=now)
    e2 = await create_entry(db, user_id, account_id=b.id, type=EntryType.INCOME,
                            amount=Decimal("40000"), currency="KRW", transacted_at=now)
    with pytest.raises(Exception):
        await merge_transfer(db, user_id, e1.id, e2.id)


async def test_merge_transfer_same_sign_rejected(db):
    user_id, a, b = await _two_accounts(db)
    now = datetime(2026, 7, 10, 3, tzinfo=timezone.utc)
    e1 = await create_entry(db, user_id, account_id=a.id, type=EntryType.EXPENSE,
                            amount=Decimal("-50000"), currency="KRW", transacted_at=now)
    e2 = await create_entry(db, user_id, account_id=b.id, type=EntryType.EXPENSE,
                            amount=Decimal("-50000"), currency="KRW", transacted_at=now)
    with pytest.raises(Exception):
        await merge_transfer(db, user_id, e1.id, e2.id)


async def test_merge_transfer_already_grouped_rejected(db):
    user_id, a, b = await _two_accounts(db)
    now = datetime(2026, 7, 10, 3, tzinfo=timezone.utc)
    out = await create_entry(db, user_id, account_id=a.id, type=EntryType.EXPENSE,
                             amount=Decimal("-50000"), currency="KRW", transacted_at=now)
    inn = await create_entry(db, user_id, account_id=b.id, type=EntryType.INCOME,
                             amount=Decimal("50000"), currency="KRW", transacted_at=now)
    await merge_transfer(db, user_id, out.id, inn.id)
    # 이미 그룹에 묶인 다리를 또 병합 시도
    other = await create_entry(db, user_id, account_id=b.id, type=EntryType.INCOME,
                               amount=Decimal("50000"), currency="KRW", transacted_at=now)
    with pytest.raises(Exception):
        await merge_transfer(db, user_id, out.id, other.id)


# ═══ 이체 후보 탐지 ═══


async def _batch_with_row(db, user_id, account_id, amount, dedup="new", status="review"):
    batch = ImportBatch(user_id=user_id, account_id=account_id, filename="f.csv",
                        file_hash=uuid.uuid4().hex, status=status)
    db.add(batch)
    await db.flush()
    row = StagedEntry(batch_id=batch.id, user_id=user_id,
                      transacted_at=datetime(2026, 7, 10, 3, tzinfo=timezone.utc),
                      amount=Decimal(amount), description="스타벅스", dedup_status=dedup)
    db.add(row)
    await db.flush()
    return batch, row


async def test_detect_transfer_candidate_match(db):
    user_id, a, b = await _two_accounts(db)
    now = datetime(2026, 7, 10, 5, tzinfo=timezone.utc)
    # B은행에 반대부호 입금 (그룹 없음)
    counterpart = await create_entry(db, user_id, account_id=b.id, type=EntryType.INCOME,
                                     amount=Decimal("12000"), currency="KRW", memo="입금", transacted_at=now)
    batch, row = await _batch_with_row(db, user_id, a.id, "-12000")

    candidates = await import_service.detect_transfer_candidates(db, batch, [row])
    assert row.id in candidates
    assert candidates[row.id].entry_id == counterpart.id
    assert candidates[row.id].account_name == "B은행"
    assert candidates[row.id].amount == Decimal("12000")


async def test_detect_excludes_grouped_and_same_account(db):
    user_id, a, b = await _two_accounts(db)
    now = datetime(2026, 7, 10, 5, tzinfo=timezone.utc)
    # 같은 계좌(A)의 반대부호 → 제외
    await create_entry(db, user_id, account_id=a.id, type=EntryType.INCOME,
                       amount=Decimal("12000"), currency="KRW", transacted_at=now)
    # B의 반대부호지만 이미 그룹에 묶임 → 제외
    grp_out = await create_entry(db, user_id, account_id=a.id, type=EntryType.EXPENSE,
                                 amount=Decimal("-12000"), currency="KRW", transacted_at=now)
    grp_in = await create_entry(db, user_id, account_id=b.id, type=EntryType.INCOME,
                                amount=Decimal("12000"), currency="KRW", transacted_at=now)
    await merge_transfer(db, user_id, grp_out.id, grp_in.id)

    batch, row = await _batch_with_row(db, user_id, a.id, "-12000")
    candidates = await import_service.detect_transfer_candidates(db, batch, [row])
    assert row.id not in candidates


async def test_detect_one_to_one(db):
    user_id, a, b = await _two_accounts(db)
    now = datetime(2026, 7, 10, 5, tzinfo=timezone.utc)
    # B에 반대부호 입금 1건, staged 2건 → 1건만 후보
    await create_entry(db, user_id, account_id=b.id, type=EntryType.INCOME,
                       amount=Decimal("12000"), currency="KRW", transacted_at=now)
    batch = ImportBatch(user_id=user_id, account_id=a.id, filename="f.csv",
                        file_hash=uuid.uuid4().hex, status="review")
    db.add(batch)
    await db.flush()
    rows = [
        StagedEntry(batch_id=batch.id, user_id=user_id, transacted_at=now,
                    amount=Decimal("-12000"), dedup_status="new"),
        StagedEntry(batch_id=batch.id, user_id=user_id, transacted_at=now,
                    amount=Decimal("-12000"), dedup_status="new"),
    ]
    db.add_all(rows)
    await db.flush()
    candidates = await import_service.detect_transfer_candidates(db, batch, rows)
    assert len(candidates) == 1


# ═══ merges 포함 커밋 ═══


async def test_commit_with_merge(db):
    user_id, a, b = await _two_accounts(db)
    now = datetime(2026, 7, 10, 5, tzinfo=timezone.utc)
    counterpart = await create_entry(db, user_id, account_id=b.id, type=EntryType.INCOME,
                                     amount=Decimal("50000"), currency="KRW", memo="입금", transacted_at=now)
    batch, row = await _batch_with_row(db, user_id, a.id, "-50000")
    row.suggested_type = "expense"
    await db.flush()

    count, adj, merged = await import_service.commit_batch(
        db, batch, merges=[MergeSpec(row_id=row.id, counterpart_entry_id=counterpart.id)],
    )
    assert count == 1
    assert merged == 1
    assert batch.status == "committed"

    # 새 다리가 committed_entry_id, 그룹으로 counterpart와 묶임
    new_leg = await db.get(Entry, row.committed_entry_id)
    assert new_leg.type == EntryType.TRANSFER_OUT
    assert new_leg.entry_group_id is not None
    await db.refresh(counterpart)
    assert counterpart.type == EntryType.TRANSFER_IN
    assert counterpart.entry_group_id == new_leg.entry_group_id


# ═══ 백필 로직 (실제 마이그레이션은 plpgsql — PG에서 기능검증, 여기선 ORM 동등 재현) ═══


async def test_backfill_orphan_trade_group_logic(db):
    user_id = uuid.uuid4()
    acc = Account(user_id=user_id, account_type=AccountType.INVESTMENT, name="증권", currency="KRW")
    db.add(acc)
    await db.flush()
    now = datetime(2026, 7, 10, 3, tzinfo=timezone.utc)
    # 그룹 없는 BUY 2건 (옛 코드가 만든 형태)
    orphans = [
        Entry(user_id=user_id, account_id=acc.id, type=EntryType.BUY, amount=Decimal("-100000"),
              currency="KRW", quantity=Decimal("1"), unit_price=Decimal("100000"),
              memo="TSLA", transacted_at=now),
        Entry(user_id=user_id, account_id=acc.id, type=EntryType.SELL, amount=Decimal("120000"),
              currency="KRW", quantity=Decimal("-1"), unit_price=Decimal("120000"),
              memo="AAPL", transacted_at=now),
    ]
    db.add_all(orphans)
    await db.flush()

    # 마이그레이션과 동일 로직: 그룹 없는 BUY/SELL → TRADE 그룹 생성+링크
    from app.models.entry import EntryGroup
    orphan_rows = (await db.execute(
        select(Entry).where(
            Entry.type.in_([EntryType.BUY, EntryType.SELL]),
            Entry.entry_group_id.is_(None),
        )
    )).scalars().all()
    for e in orphan_rows:
        g = EntryGroup(user_id=e.user_id, group_type=GroupType.TRADE, description=e.memo)
        db.add(g)
        await db.flush()
        e.entry_group_id = g.id
    await db.flush()

    remaining = (await db.execute(
        select(Entry).where(
            Entry.type.in_([EntryType.BUY, EntryType.SELL]),
            Entry.entry_group_id.is_(None),
        )
    )).scalars().all()
    assert remaining == []
