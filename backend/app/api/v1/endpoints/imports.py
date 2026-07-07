import hashlib
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.import_batch import ImportBatch, StagedEntry
from app.models.user import User
from app.schemas.imports import (
    ImportBatchResponse,
    ImportCommitRequest,
    ImportCommitResponse,
    ImportDetailResponse,
    StagedEntryResponse,
    StagedEntryUpdate,
)
from app.services import import_service

router = APIRouter(tags=["imports"])


async def _get_owned_batch(
    db: AsyncSession, user_id: uuid.UUID, batch_id: uuid.UUID,
) -> ImportBatch:
    batch = await db.get(ImportBatch, batch_id)
    if not batch or batch.user_id != user_id:
        raise HTTPException(status_code=404, detail="Import batch not found")
    return batch


@router.post("", response_model=ImportBatchResponse, status_code=status.HTTP_201_CREATED)
async def create_import(
    file: UploadFile = File(...),
    account_id: uuid.UUID | None = Form(None),
    password: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    existing = (await db.execute(
        select(ImportBatch).where(
            ImportBatch.user_id == current_user.id,
            ImportBatch.file_hash == file_hash,
        )
    )).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="이미 업로드된 파일입니다")

    batch = ImportBatch(
        user_id=current_user.id,
        account_id=account_id,
        filename=file.filename or "upload",
        file_hash=file_hash,
        status="uploaded",
        raw_file=content,
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)

    from app.tasks.import_tasks import parse_import_batch

    parse_import_batch.delay(str(batch.id), password)
    return batch


@router.get("", response_model=list[ImportBatchResponse])
async def list_imports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(ImportBatch)
        .where(ImportBatch.user_id == current_user.id)
        .order_by(ImportBatch.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{batch_id}", response_model=ImportDetailResponse)
async def get_import(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    batch = await _get_owned_batch(db, current_user.id, batch_id)
    staged = (await db.execute(
        select(StagedEntry)
        .where(StagedEntry.batch_id == batch.id)
        .order_by(StagedEntry.transacted_at)
    )).scalars().all()
    balance_check = await import_service.compute_balance_check(db, batch)
    period_overlap = await import_service.check_period_overlap(db, batch)
    candidates = await import_service.detect_transfer_candidates(db, batch, list(staged))

    staged_responses = []
    for s in staged:
        resp = StagedEntryResponse.model_validate(s)
        resp.transfer_candidate = candidates.get(s.id)
        staged_responses.append(resp)

    return ImportDetailResponse(
        batch=ImportBatchResponse.model_validate(batch),
        staged_entries=staged_responses,
        balance_check=balance_check,
        period_overlap=period_overlap,
    )


@router.patch("/{batch_id}/rows/{row_id}", response_model=StagedEntryResponse)
async def update_row(
    batch_id: uuid.UUID,
    row_id: uuid.UUID,
    data: StagedEntryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    batch = await _get_owned_batch(db, current_user.id, batch_id)
    staged = await db.get(StagedEntry, row_id)
    if not staged or staged.batch_id != batch.id:
        raise HTTPException(status_code=404, detail="Row not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(staged, field, value)
    await db.commit()
    await db.refresh(staged)
    return staged


@router.post("/{batch_id}/commit", response_model=ImportCommitResponse)
async def commit_import(
    batch_id: uuid.UUID,
    data: ImportCommitRequest = ImportCommitRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    batch = await _get_owned_batch(db, current_user.id, batch_id)
    count, adjustment_created, merged_count = await import_service.commit_batch(
        db, batch, create_adjustment=data.create_adjustment, merges=data.merges,
    )
    await db.commit()
    return ImportCommitResponse(
        committed_count=count,
        adjustment_created=adjustment_created,
        merged_count=merged_count,
    )


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_import(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    batch = await _get_owned_batch(db, current_user.id, batch_id)
    if batch.status == "committed":
        raise HTTPException(status_code=400, detail="커밋된 배치는 삭제할 수 없습니다")
    await db.delete(batch)
    await db.commit()
