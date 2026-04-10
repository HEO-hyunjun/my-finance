export type EntryType =
  | 'income' | 'expense'
  | 'transfer_in' | 'transfer_out'
  | 'buy' | 'sell'
  | 'dividend' | 'interest' | 'fee' | 'adjustment';

export type EntryGroupType = 'transfer' | 'trade' | 'adjustment';

export interface Entry {
  id: string;
  account_id: string;
  entry_group_id: string | null;
  category_id: string | null;
  security_id: string | null;
  type: EntryType;
  amount: number;
  currency: string;
  quantity: number | null;
  unit_price: number | null;
  fee: number;
  exchange_rate: number | null;
  memo: string | null;
  recurring_schedule_id: string | null;
  transacted_at: string;
  created_at: string;
}

export interface EntryGroup {
  id: string;
  user_id: string;
  group_type: EntryGroupType;
  description: string | null;
  created_at: string;
  entries: Entry[];
}

export interface EntryCreate {
  account_id: string;
  type: EntryType;
  amount: number;
  currency?: string;
  category_id?: string | null;
  security_id?: string | null;
  quantity?: number | null;
  unit_price?: number | null;
  fee?: number;
  exchange_rate?: number | null;
  memo?: string | null;
  transacted_at: string;
}

export interface EntryUpdate {
  amount?: number | null;
  category_id?: string | null;
  memo?: string | null;
  quantity?: number | null;
  unit_price?: number | null;
  fee?: number | null;
  transacted_at?: string | null;
}

export interface TransferRequest {
  source_account_id: string;
  target_account_id: string;
  amount: number;
  currency?: string;
  memo?: string | null;
  transacted_at?: string | null;
}

export interface TradeRequest {
  account_id: string;
  security_id: string;
  trade_type: 'buy' | 'sell';
  quantity: number;
  unit_price: number;
  currency?: string;
  fee?: number;
  exchange_rate?: number | null;
  memo?: string | null;
  transacted_at?: string | null;
}

export interface EntryListResponse {
  data: Entry[];
  total: number;
  page: number;
  per_page: number;
}

export interface EntryFilters {
  account_id?: string;
  type?: string;
  category_id?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  per_page?: number;
}
