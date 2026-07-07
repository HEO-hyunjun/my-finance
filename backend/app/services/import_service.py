"""거래내역 임포트 서비스.

결정적 추출(import_parser) → LLM 정규화 → 결정적 중복/잔액 검증의 오케스트레이션.
LLM 응답은 신뢰하지 않고 중복/합계/잔액 검증은 전부 코드로 수행한다.
"""

import json
import logging
import re
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.tz import kst_day_utc_range, kst_noon_utc
from app.models.category import Category
from app.models.entry import Entry, EntryType
from app.models.import_batch import ImportBatch, StagedEntry
from app.schemas.imports import BalanceCheck, TransferCandidate
from app.services import entry_service
from app.services.import_parser import ImportParseError, extract_rows

logger = logging.getLogger(__name__)


def _normalize_description(text: str | None) -> str:
    """공백/특수문자 제거 + 소문자 — 중복 판정용 정규화."""
    if not text:
        return ""
    return re.sub(r"[^0-9a-z가-힣]", "", text.lower())


def _parse_llm_json(content: str) -> dict:
    content = content.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    return json.loads(content)


def _build_prompt(chunk: list[list[str]], category_names: list[str]) -> str:
    rows_text = "\n".join(" | ".join(cell for cell in row) for row in chunk)
    cats = ", ".join(category_names) if category_names else "(없음)"
    return (
        "다음은 은행/카드 거래내역 파일에서 추출한 표 데이터다. 각 거래를 정규화해라.\n"
        "규칙: 입금은 amount 양수, 출금은 음수. 날짜는 ISO(YYYY-MM-DD). "
        "suggested_type은 income 또는 expense. suggested_category는 아래 목록 중 하나이거나 null.\n"
        f"카테고리 목록: {cats}\n\n"
        f"표 데이터:\n{rows_text}\n\n"
        "JSON만 출력. 형식:\n"
        '{"source_bank": "은행명 추정 또는 null", "entries": ['
        '{"transacted_at": "YYYY-MM-DD", "amount": -12000, "description": "스타벅스", '
        '"balance_after": 530000, "suggested_type": "expense", "suggested_category": "식비"}]}'
    )


async def normalize_rows(rows: list[list[str]], categories: list[Category]) -> dict:
    """LLM 정규화. rows를 청크로 나눠 호출하고 결과를 병합한다."""
    from litellm import acompletion

    category_names = [c.name for c in categories]
    chunk_size = max(1, settings.IMPORT_LLM_CHUNK_SIZE)
    entries: list[dict] = []
    source_bank: str | None = None

    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        response = await acompletion(
            model=settings.import_model,
            messages=[{"role": "user", "content": _build_prompt(chunk, category_names)}],
            max_tokens=settings.IMPORT_MAX_TOKENS,
            temperature=0,
            drop_params=True,
        )
        data = _parse_llm_json(response.choices[0].message.content)
        source_bank = source_bank or data.get("source_bank")
        entries.extend(data.get("entries", []))

    return {"source_bank": source_bank, "entries": entries}


def _to_decimal(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _parse_transacted_at(raw: str) -> datetime:
    dt = datetime.fromisoformat(str(raw))
    if dt.tzinfo is None and dt.hour == 0 and dt.minute == 0 and dt.second == 0:
        # 날짜만 온 경우 KST 정오의 UTC로 저장 (일 단위 중복 매칭 안정)
        return kst_noon_utc(dt.date())
    return dt


async def parse_batch(
    db: AsyncSession,
    batch: ImportBatch,
    password: str | None = None,
    normalizer=None,
    extractor=extract_rows,
) -> ImportBatch:
    """추출→LLM→중복판정. 성공 시 status=review, 실패 시 status=failed."""
    normalizer = normalizer or normalize_rows
    batch.status = "parsing"
    await db.flush()

    try:
        rows = extractor(batch.raw_file, batch.filename, password)
    except ImportParseError as e:
        batch.status = "failed"
        batch.error = str(e)
        await db.flush()
        return batch
    except Exception as e:  # noqa: BLE001 - 추출 단계 오류를 배치에 기록
        batch.status = "failed"
        batch.error = f"추출 오류: {e}"
        await db.flush()
        return batch

    categories = (await db.execute(
        select(Category).where(Category.user_id == batch.user_id, Category.is_active.is_(True))
    )).scalars().all()
    cat_by_name = {c.name: c for c in categories}

    try:
        result = await normalizer(rows, categories)
    except Exception as e:  # noqa: BLE001 - LLM/파싱 실패를 배치에 기록
        batch.status = "failed"
        batch.error = f"정규화 오류: {e}"
        await db.flush()
        return batch

    batch.source_bank = result.get("source_bank")
    normalized = result.get("entries", [])

    staged_list: list[StagedEntry] = []
    for item in normalized:
        amount = _to_decimal(item.get("amount"))
        if amount is None:
            continue
        try:
            transacted_at = _parse_transacted_at(item.get("transacted_at"))
        except (ValueError, TypeError):
            continue
        cat = cat_by_name.get(item.get("suggested_category"))
        staged = StagedEntry(
            batch_id=batch.id,
            user_id=batch.user_id,
            transacted_at=transacted_at,
            amount=amount,
            description=item.get("description"),
            balance_after=_to_decimal(item.get("balance_after")),
            suggested_type=item.get("suggested_type"),
            suggested_category_id=cat.id if cat else None,
        )
        db.add(staged)
        staged_list.append(staged)

    await db.flush()

    # 결정적 중복 판정 (계좌가 지정된 경우에만 원장과 대조)
    if batch.account_id is not None:
        for staged in staged_list:
            await _classify_dedup(db, batch.account_id, staged)

    if staged_list:
        dates = [s.transacted_at.date() for s in staged_list]
        batch.period_start = min(dates)
        batch.period_end = max(dates)
    batch.row_count = len(staged_list)
    batch.status = "review"
    await db.flush()
    return batch


async def _classify_dedup(
    db: AsyncSession, account_id: uuid.UUID, staged: StagedEntry,
) -> None:
    day_start, day_end = kst_day_utc_range(staged.transacted_at.date())
    matches = (await db.execute(
        select(Entry).where(
            Entry.account_id == account_id,
            Entry.transacted_at >= day_start,
            Entry.transacted_at < day_end,
            Entry.amount == staged.amount,
        )
    )).scalars().all()

    if not matches:
        staged.dedup_status = "new"
        return

    norm = _normalize_description(staged.description)
    exact = next((m for m in matches if _normalize_description(m.memo) == norm), None)
    if exact is not None:
        staged.dedup_status = "exact"
        staged.matched_entry_id = exact.id
        staged.is_selected = False  # 이미 있는 거래는 기본 해제
    else:
        staged.dedup_status = "probable"
        staged.matched_entry_id = matches[0].id


async def compute_balance_check(db: AsyncSession, batch: ImportBatch) -> BalanceCheck:
    """파일 마지막 balance_after vs 그 계좌의 현재 원장 잔액."""
    file_balance = None
    staged = (await db.execute(
        select(StagedEntry)
        .where(StagedEntry.batch_id == batch.id, StagedEntry.balance_after.is_not(None))
        .order_by(StagedEntry.transacted_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    if staged is not None:
        file_balance = staged.balance_after

    ledger_balance = None
    if batch.account_id is not None:
        from app.models.account import Account

        account = await db.get(Account, batch.account_id)
        if account is not None:
            ledger_balance = await entry_service.get_account_balance(
                db, batch.account_id, account.currency,
            )

    difference = None
    if file_balance is not None and ledger_balance is not None:
        difference = file_balance - ledger_balance

    return BalanceCheck(
        file_balance=file_balance,
        ledger_balance=ledger_balance,
        difference=difference,
    )


async def check_period_overlap(db: AsyncSession, batch: ImportBatch) -> bool:
    """같은 유저의 다른 배치와 기간이 겹치는지."""
    if batch.period_start is None or batch.period_end is None:
        return False
    stmt = select(func.count()).select_from(ImportBatch).where(
        ImportBatch.user_id == batch.user_id,
        ImportBatch.id != batch.id,
        ImportBatch.status != "failed",
        ImportBatch.period_start.is_not(None),
        ImportBatch.period_end.is_not(None),
        ImportBatch.period_start <= batch.period_end,
        ImportBatch.period_end >= batch.period_start,
    )
    return ((await db.execute(stmt)).scalar() or 0) > 0


async def detect_transfer_candidates(
    db: AsyncSession, batch: ImportBatch, staged_rows: list[StagedEntry],
) -> dict[uuid.UUID, TransferCandidate]:
    """dedup_status='new' 행마다 다른 계좌의 반대부호 이체 상대를 1:1로 찾는다.

    저장하지 않고 동적으로 계산한다. 계좌 미지정 배치는 빈 결과.
    """
    from app.models.account import Account

    result: dict[uuid.UUID, TransferCandidate] = {}
    if batch.account_id is None:
        return result
    account = await db.get(Account, batch.account_id)
    if account is None:
        return result

    used_entry_ids: set[uuid.UUID] = set()
    for staged in staged_rows:
        if staged.dedup_status != "new":
            continue
        day_start, day_end = kst_day_utc_range(staged.transacted_at.date())
        matches = (await db.execute(
            select(Entry).where(
                Entry.user_id == batch.user_id,
                Entry.account_id != batch.account_id,
                Entry.entry_group_id.is_(None),
                Entry.type.in_([EntryType.INCOME, EntryType.EXPENSE]),
                Entry.currency == account.currency,
                Entry.transacted_at >= day_start,
                Entry.transacted_at < day_end,
                Entry.amount == -staged.amount,
            ).order_by(Entry.transacted_at)
        )).scalars().all()
        candidate = next((m for m in matches if m.id not in used_entry_ids), None)
        if candidate is None:
            continue
        used_entry_ids.add(candidate.id)
        cand_account = await db.get(Account, candidate.account_id)
        result[staged.id] = TransferCandidate(
            entry_id=candidate.id,
            account_name=cand_account.name if cand_account else "(알 수 없음)",
            transacted_at=candidate.transacted_at,
            amount=candidate.amount,
        )
    return result


async def commit_batch(
    db: AsyncSession,
    batch: ImportBatch,
    create_adjustment: bool = False,
    merges: list | None = None,
) -> tuple[int, bool, int]:
    """선택된 staged 행을 Entry로 일괄 생성 (source='import'). 단일 트랜잭션.

    merges의 각 {row_id, counterpart_entry_id}는 해당 행의 새 Entry를 만든 뒤
    counterpart 기존 Entry와 이체 그룹으로 병합한다.
    """
    from fastapi import HTTPException

    if batch.status != "review":
        raise HTTPException(status_code=400, detail="review 상태의 배치만 커밋할 수 있습니다")
    if batch.account_id is None:
        raise HTTPException(status_code=400, detail="계좌가 지정되지 않았습니다")

    from app.models.account import Account

    account = await db.get(Account, batch.account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="계좌를 찾을 수 없습니다")

    merge_map = {m.row_id: m.counterpart_entry_id for m in (merges or [])}

    staged_rows = (await db.execute(
        select(StagedEntry).where(
            StagedEntry.batch_id == batch.id,
            StagedEntry.is_selected.is_(True),
            StagedEntry.committed_entry_id.is_(None),
        )
    )).scalars().all()

    count = 0
    merged_count = 0
    for staged in staged_rows:
        if staged.suggested_type in ("income", "expense"):
            entry_type = EntryType(staged.suggested_type)
        else:
            entry_type = EntryType.INCOME if staged.amount >= 0 else EntryType.EXPENSE
        entry = await entry_service.create_entry(
            db,
            user_id=batch.user_id,
            account_id=batch.account_id,
            type=entry_type,
            amount=staged.amount,
            currency=account.currency,
            category_id=staged.suggested_category_id,
            memo=staged.description,
            source="import",
            transacted_at=staged.transacted_at,
        )
        staged.committed_entry_id = entry.id
        count += 1

        if staged.id in merge_map:
            # 새로 만든 다리를 기존 반대편 거래와 이체 그룹으로 병합
            await entry_service.merge_transfer(
                db, batch.user_id, entry.id, merge_map[staged.id],
            )
            merged_count += 1

    adjustment_created = False
    if create_adjustment:
        check = await compute_balance_check(db, batch)
        if check.file_balance is not None and check.difference not in (None, Decimal("0")):
            await entry_service.adjust_balance(
                db,
                user_id=batch.user_id,
                account_id=batch.account_id,
                target_balance=check.file_balance,
                currency=account.currency,
                memo="임포트 잔액 보정",
            )
            adjustment_created = True

    batch.status = "committed"
    await db.flush()
    return count, adjustment_created, merged_count
