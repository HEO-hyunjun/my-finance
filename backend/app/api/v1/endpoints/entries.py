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
        base = base.where(Entry.type == type)
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
    entry = await entry_service.create_entry(
        db,
        user_id=current_user.id,
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
    group = await entry_service.create_transfer(
        db,
        user_id=current_user.id,
        source_account_id=data.source_account_id,
        target_account_id=data.target_account_id,
        amount=data.amount,
        currency=data.currency,
        memo=data.memo,
        transacted_at=data.transacted_at,
    )
    await db.commit()
    # Return both entries in the group
    stmt = select(Entry).where(Entry.entry_group_id == group.id)
    entries = list((await db.execute(stmt)).scalars().all())
    return entries


@router.post("/trade", response_model=list[EntryResponse])
async def create_trade(
    data: TradeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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

    for field, value in data.model_dump(exclude_unset=True).items():
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
    await db.delete(entry)
    await db.commit()
