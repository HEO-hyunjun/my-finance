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


class ImportCommitResponse(BaseModel):
    committed_count: int
    adjustment_created: bool
