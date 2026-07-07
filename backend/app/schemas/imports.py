from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ImportBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID | None
    filename: str
    source_bank: str | None
    status: str
    period_start: date | None
    period_end: date | None
    row_count: int | None
    error: str | None
    created_at: datetime


class TransferCandidate(BaseModel):
    """이체 상대 후보 (다른 계좌의 반대부호 거래) — 동적 계산, 저장 안 함."""
    entry_id: UUID
    account_name: str
    transacted_at: datetime
    amount: Decimal


class StagedEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transacted_at: datetime
    amount: Decimal
    description: str | None
    balance_after: Decimal | None
    suggested_type: str | None
    suggested_category_id: UUID | None
    dedup_status: str
    matched_entry_id: UUID | None
    is_selected: bool
    committed_entry_id: UUID | None
    transfer_candidate: TransferCandidate | None = None


class BalanceCheck(BaseModel):
    file_balance: Decimal | None
    ledger_balance: Decimal | None
    difference: Decimal | None


class ImportDetailResponse(BaseModel):
    batch: ImportBatchResponse
    staged_entries: list[StagedEntryResponse]
    balance_check: BalanceCheck
    period_overlap: bool


class StagedEntryUpdate(BaseModel):
    suggested_category_id: UUID | None = None
    suggested_type: str | None = None
    is_selected: bool | None = None


class MergeSpec(BaseModel):
    row_id: UUID
    counterpart_entry_id: UUID


class ImportCommitRequest(BaseModel):
    create_adjustment: bool = False
    merges: list[MergeSpec] = []


class ImportCommitResponse(BaseModel):
    committed_count: int
    adjustment_created: bool
    merged_count: int = 0
