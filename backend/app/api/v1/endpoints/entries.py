import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.entry import Entry, EntryType
from app.models.user import User
from app.schemas.entry import (
    EntryCreate,
    EntryListResponse,
    EntryResponse,
    EntryUpdate,
    TradeRequest,
    TransferRequest,
)
from app.services import entry_service

router = APIRouter(tags=["entries"])


@router.get("", response_model=EntryListResponse)
async def list_entries(
    account_id: uuid.UUID | None = Query(None),
    type: str | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Base query
    base = select(Entry).where(Entry.user_id == current_user.id)

    # Filters
    if account_id:
        base = base.where(Entry.account_id == account_id)
    if type:
        type_list = [t.strip() for t in type.split(",") if t.strip()]
        if len(type_list) == 1:
            base = base.where(Entry.type == type_list[0])
        else:
            base = base.where(Entry.type.in_(type_list))
    if category_id:
        base = base.where(Entry.category_id == category_id)
    if start_date:
        base = base.where(Entry.transacted_at >= start_date)
    if end_date:
        base = base.where(Entry.transacted_at <= end_date)

    # Total count
    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Paginated data
    data_stmt = (
        base.order_by(Entry.transacted_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    entries = list((await db.execute(data_stmt)).scalars().all())

    return EntryListResponse(
        data=entries,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("", response_model=EntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    data: EntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.account import Account

    account = (
        await db.execute(
            select(Account).where(
                Account.id == data.account_id, Account.user_id == current_user.id
            )
        )
    ).scalar_one_or_none()
    if not account:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="계좌를 찾을 수 없습니다")

    from app.models.account import AccountType

    if account.account_type != AccountType.INVESTMENT and data.currency != account.currency:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail=f"통화가 계좌 통화({account.currency})와 일치해야 합니다",
        )

    entry = await entry_service.create_entry(
        db,
        user_id=current_user.id,
        source="manual",
        **data.model_dump(),
    )
    await db.commit()
    await db.refresh(entry)
    return entry


@router.post("/transfer", response_model=list[EntryResponse])
async def create_transfer(
    data: TransferRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from fastapi import HTTPException

    from app.models.account import Account

    accounts = {}
    for aid, label in [
        (data.source_account_id, "출금"),
        (data.target_account_id, "입금"),
    ]:
        acc = (
            await db.execute(
                select(Account).where(
                    Account.id == aid, Account.user_id == current_user.id
                )
            )
        ).scalar_one_or_none()
        if not acc:
            raise HTTPException(
                status_code=404, detail=f"{label} 계좌를 찾을 수 없습니다"
            )
        accounts[aid] = acc

    src = accounts[data.source_account_id]
    tgt = accounts[data.target_account_id]

    group = await entry_service.create_transfer(
        db,
        user_id=current_user.id,
        source_account_id=data.source_account_id,
        target_account_id=data.target_account_id,
        amount=data.amount,
        currency=src.currency,
        target_currency=tgt.currency,
        target_amount=data.target_amount,
        exchange_rate=data.exchange_rate,
        memo=data.memo,
        transacted_at=data.transacted_at,
        source="manual",
    )
    await db.commit()
    stmt = select(Entry).where(Entry.entry_group_id == group.id)
    entries = list((await db.execute(stmt)).scalars().all())
    return entries


@router.post("/trade", response_model=list[EntryResponse])
async def create_trade(
    data: TradeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from fastapi import HTTPException

    from app.models.account import Account

    acc = (
        await db.execute(
            select(Account).where(
                Account.id == data.account_id, Account.user_id == current_user.id
            )
        )
    ).scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=404, detail="계좌를 찾을 수 없습니다")

    trade_type = EntryType(data.trade_type)
    group = await entry_service.create_trade(
        db,
        user_id=current_user.id,
        account_id=data.account_id,
        security_id=data.security_id,
        trade_type=trade_type,
        quantity=data.quantity,
        unit_price=data.unit_price,
        currency=data.currency,
        fee=data.fee,
        exchange_rate=data.exchange_rate,
        memo=data.memo,
        transacted_at=data.transacted_at,
        source="manual",
    )
    await db.commit()
    stmt = select(Entry).where(Entry.entry_group_id == group.id)
    entries = list((await db.execute(stmt)).scalars().all())
    return entries


@router.get("/{entry_id}", response_model=EntryResponse)
async def get_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Entry).where(
        Entry.id == entry_id, Entry.user_id == current_user.id
    )
    entry = (await db.execute(stmt)).scalar_one_or_none()
    if not entry:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.patch("/{entry_id}", response_model=EntryResponse)
async def update_entry(
    entry_id: uuid.UUID,
    data: EntryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Entry).where(
        Entry.id == entry_id, Entry.user_id == current_user.id
    )
    entry = (await db.execute(stmt)).scalar_one_or_none()
    if not entry:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Entry not found")

    changes = data.model_dump(exclude_unset=True)
    if entry.entry_group_id is not None:
        # 그룹 소속 entry는 memo/category만 개별 수정 가능,
        # 금액·수량·일시 변경은 그룹 API로 양다리를 함께 수정해야 함
        restricted = {"amount", "quantity", "unit_price", "fee", "transacted_at"}
        if restricted & changes.keys():
            from fastapi import HTTPException

            raise HTTPException(
                status_code=409,
                detail={
                    "message": "이체/매매 항목의 금액·수량·일시는 그룹 API로 수정하세요",
                    "entry_group_id": str(entry.entry_group_id),
                },
            )

    for field, value in changes.items():
        setattr(entry, field, value)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Entry).where(
        Entry.id == entry_id, Entry.user_id == current_user.id
    )
    entry = (await db.execute(stmt)).scalar_one_or_none()
    if not entry:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Entry not found")
    if entry.entry_group_id is not None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=409,
            detail={
                "message": "이체/매매 항목은 그룹 API로 삭제하세요 (양다리가 함께 삭제됩니다)",
                "entry_group_id": str(entry.entry_group_id),
            },
        )
    await db.delete(entry)
    await db.commit()
