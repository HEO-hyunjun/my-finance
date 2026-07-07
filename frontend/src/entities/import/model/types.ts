export type ImportStatus = 'uploaded' | 'parsing' | 'review' | 'committed' | 'failed';

export type DedupStatus = 'new' | 'exact' | 'probable';

export interface ImportBatch {
  id: string;
  account_id: string | null;
  filename: string;
  source_bank: string | null;
  status: ImportStatus;
  period_start: string | null;
  period_end: string | null;
  row_count: number | null;
  error: string | null;
  created_at: string;
}

export interface StagedEntry {
  id: string;
  transacted_at: string;
  amount: number;
  description: string | null;
  balance_after: number | null;
  suggested_type: string | null;
  suggested_category_id: string | null;
  dedup_status: DedupStatus;
  matched_entry_id: string | null;
  is_selected: boolean;
  committed_entry_id: string | null;
}

export interface BalanceCheck {
  file_balance: number | null;
  ledger_balance: number | null;
  difference: number | null;
}

export interface ImportDetail {
  batch: ImportBatch;
  staged_entries: StagedEntry[];
  balance_check: BalanceCheck;
  period_overlap: boolean;
}

export interface StagedEntryUpdate {
  suggested_category_id?: string | null;
  suggested_type?: string | null;
  is_selected?: boolean;
}

export interface ImportCommitResponse {
  committed_count: number;
  adjustment_created: boolean;
}
