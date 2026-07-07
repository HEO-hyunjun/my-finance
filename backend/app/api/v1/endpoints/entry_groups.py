import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.entry import Entry, GroupType
from app.models.user import User
from app.schemas.entry import EntryGroupResponse, EntryGroupUpdate, MergeTransferRequest
from app.services import entry_service

router = APIRouter(tags=["entry-groups"])


@router.post("/merge-transfer", response_model=EntryGroupResponse)
async def merge_transfer(
    data: MergeTransferRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = await entry_service.merge_transfer(
        db, current_user.id, data.entry_a_id, data.entry_b_id,
    )
    await db.commit()
    return await _to_response(db, group)


async def _to_response(db: AsyncSession, group) -> EntryGroupResponse:
    stmt = select(Entry).where(Entry.entry_group_id == group.id)
    entries = list((await db.execute(stmt)).scalars().all())
    return EntryGroupResponse(
        id=group.id,
        group_type=group.group_type.value,
        description=group.description,
        created_at=group.created_at,
        entries=entries,
    )


@router.get("/{group_id}", response_model=EntryGroupResponse)
async def get_entry_group(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = await entry_service.get_entry_group(db, current_user.id, group_id)
    return await _to_response(db, group)


@router.patch("/{group_id}", response_model=EntryGroupResponse)
async def update_entry_group(
    group_id: uuid.UUID,
    data: EntryGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = await entry_service.get_entry_group(db, current_user.id, group_id)

    if group.group_type == GroupType.TRANSFER:
        group = await entry_service.update_transfer_group(
            db,
            current_user.id,
            group_id,
            amount=data.amount,
            target_amount=data.target_amount,
            exchange_rate=data.exchange_rate,
            memo=data.memo,
            transacted_at=data.transacted_at,
        )
    elif group.group_type == GroupType.TRADE:
        group = await entry_service.update_trade_group(
            db,
            current_user.id,
            group_id,
            quantity=data.quantity,
            unit_price=data.unit_price,
            fee=data.fee,
            memo=data.memo,
            transacted_at=data.transacted_at,
        )
    else:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Unsupported group type")

    await db.commit()
    return await _to_response(db, group)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry_group(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await entry_service.delete_entry_group(db, current_user.id, group_id)
    await db.commit()
