"""Phase 4 임포트 파이프라인 테스트.

- 결정적 추출 (csv/xlsx)
- LLM 정규화는 fake normalizer로 주입 (실 API 호출 없음)
- 중복 판정 exact/probable/new
- commit 트랜잭션 (선택 행만 source='import' 생성)
- file_hash 중복 409
- 잔액 차이 계산
"""

import io
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.deps import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.account import Account, AccountType
from app.models.entry import Entry, EntryType
from app.models.import_batch import ImportBatch, StagedEntry
from app.models.user import User
from app.services import import_service
from app.services.entry_service import create_entry
from app.services.import_parser import extract_rows


def _fake_normalizer(entries):
    async def _norm(rows, categories):
        return {"source_bank": "테스트은행", "entries": entries}
    return _norm


async def _account(db, currency="KRW"):
    user_id = uuid.uuid4()
    acc = Account(user_id=user_id, account_type=AccountType.CASH, name="통장", currency=currency)
    db.add(acc)
    await db.flush()
    return user_id, acc


async def _batch(db, user_id, account_id, raw=b"x,y,z\n"):
    batch = ImportBatch(
        user_id=user_id, account_id=account_id, filename="stmt.csv",
        file_hash=uuid.uuid4().hex, status="uploaded", raw_file=raw,
    )
    db.add(batch)
    await db.flush()
    return batch


# ═══ 추출 ═══


def test_extract_rows_csv():
    content = "2026-07-10,스타벅스,-12000\n2026-07-11,급여,3000000\n".encode()
    rows = extract_rows(content, "stmt.csv")
    assert rows[0][0] == "2026-07-10"
    assert rows[0][1] == "스타벅스"
    assert rows[1][2] == "3000000"


def test_extract_rows_xlsx():
    buf = io.BytesIO()
    pd.DataFrame(
        [["2026-07-10", "스타벅스", "-12000"], ["2026-07-11", "급여", "3000000"]]
    ).to_excel(buf, index=False, header=False, engine="openpyxl")
    rows = extract_rows(buf.getvalue(), "stmt.xlsx")
    assert rows[0][1] == "스타벅스"
    assert rows[1][0] == "2026-07-11"


# ═══ parse_batch + 중복 판정 ═══


async def test_parse_batch_new_and_exact(db):
    user_id, acc = await _account(db)
    # 기존 원장에 동일 거래 (2026-07-10, -12000, 스타벅스)
    await create_entry(db, user_id, account_id=acc.id, type=EntryType.EXPENSE,
                       amount=Decimal("-12000"), currency="KRW", memo="스타벅스",
                       transacted_at=datetime(2026, 7, 10, 3, tzinfo=timezone.utc))
    batch = await _batch(db, user_id, acc.id)

    entries = [
        {"transacted_at": "2026-07-10", "amount": -12000, "description": "스타벅스",
         "balance_after": 488000, "suggested_type": "expense", "suggested_category": None},
        {"transacted_at": "2026-07-11", "amount": 3000000, "description": "급여",
         "balance_after": 3488000, "suggested_type": "income", "suggested_category": None},
    ]
    await import_service.parse_batch(db, batch, normalizer=_fake_normalizer(entries))

    assert batch.status == "review"
    assert batch.row_count == 2
    assert batch.source_bank == "테스트은행"

    staged = (await db.execute(
        select(StagedEntry).where(StagedEntry.batch_id == batch.id).order_by(StagedEntry.transacted_at)
    )).scalars().all()
    starbucks = next(s for s in staged if s.description == "스타벅스")
    salary = next(s for s in staged if s.description == "급여")
    assert starbucks.dedup_status == "exact"
    assert starbucks.is_selected is False
    assert starbucks.matched_entry_id is not None
    assert salary.dedup_status == "new"
    assert salary.is_selected is True


async def test_parse_batch_probable(db):
    user_id, acc = await _account(db)
    # 같은 날짜/금액이지만 설명이 다른 기존 거래 → probable
    await create_entry(db, user_id, account_id=acc.id, type=EntryType.EXPENSE,
                       amount=Decimal("-12000"), currency="KRW", memo="편의점",
                       transacted_at=datetime(2026, 7, 10, 3, tzinfo=timezone.utc))
    batch = await _batch(db, user_id, acc.id)
    entries = [{"transacted_at": "2026-07-10", "amount": -12000, "description": "스타벅스",
                "balance_after": None, "suggested_type": "expense", "suggested_category": None}]
    await import_service.parse_batch(db, batch, normalizer=_fake_normalizer(entries))

    staged = (await db.execute(
        select(StagedEntry).where(StagedEntry.batch_id == batch.id)
    )).scalar_one()
    assert staged.dedup_status == "probable"
    assert staged.is_selected is True
    assert staged.matched_entry_id is not None


# ═══ commit ═══


async def test_commit_batch_creates_selected_only(db):
    user_id, acc = await _account(db)
    batch = await _batch(db, user_id, acc.id)
    entries = [
        {"transacted_at": "2026-07-11", "amount": 3000000, "description": "급여",
         "balance_after": None, "suggested_type": "income", "suggested_category": None},
        {"transacted_at": "2026-07-12", "amount": -5000, "description": "커피",
         "balance_after": None, "suggested_type": "expense", "suggested_category": None},
    ]
    await import_service.parse_batch(db, batch, normalizer=_fake_normalizer(entries))

    staged = (await db.execute(
        select(StagedEntry).where(StagedEntry.batch_id == batch.id)
    )).scalars().all()
    # 커피 행만 해제
    for s in staged:
        if s.description == "커피":
            s.is_selected = False
    await db.flush()

    count, adj, merged = await import_service.commit_batch(db, batch)
    assert count == 1
    assert adj is False
    assert merged == 0
    assert batch.status == "committed"

    imported = (await db.execute(
        select(Entry).where(Entry.account_id == acc.id, Entry.source == "import")
    )).scalars().all()
    assert len(imported) == 1
    assert imported[0].memo == "급여"
    assert imported[0].type == EntryType.INCOME

    salary_staged = next(s for s in staged if s.description == "급여")
    assert salary_staged.committed_entry_id == imported[0].id


# ═══ 잔액 차이 ═══


async def test_balance_check_difference(db):
    user_id, acc = await _account(db)
    # 원장 잔액 500,000
    await create_entry(db, user_id, account_id=acc.id, type=EntryType.INCOME,
                       amount=Decimal("500000"), currency="KRW",
                       transacted_at=datetime(2026, 7, 1, tzinfo=timezone.utc))
    batch = await _batch(db, user_id, acc.id)
    entries = [{"transacted_at": "2026-07-11", "amount": 3000000, "description": "급여",
                "balance_after": 530000, "suggested_type": "income", "suggested_category": None}]
    await import_service.parse_batch(db, batch, normalizer=_fake_normalizer(entries))

    check = await import_service.compute_balance_check(db, batch)
    assert check.file_balance == Decimal("530000")
    assert check.ledger_balance == Decimal("500000")
    assert check.difference == Decimal("30000")


# ═══ 엔드포인트: file_hash 중복 409 ═══


async def test_duplicate_file_hash_409(db, monkeypatch):
    from app.tasks import import_tasks
    monkeypatch.setattr(import_tasks.parse_import_batch, "delay", lambda *a, **k: None)

    user = User(id=uuid.uuid4(), email=f"{uuid.uuid4()}@t.com", hashed_password="x", name="t")
    db.add(user)
    await db.flush()

    async def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: user
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    try:
        files = {"file": ("stmt.csv", b"2026-07-10,coffee,-1000\n", "text/csv")}
        r1 = await client.post("/api/v1/imports", files=files)
        assert r1.status_code == 201
        files2 = {"file": ("stmt.csv", b"2026-07-10,coffee,-1000\n", "text/csv")}
        r2 = await client.post("/api/v1/imports", files=files2)
        assert r2.status_code == 409
    finally:
        app.dependency_overrides.clear()
        await client.aclose()
