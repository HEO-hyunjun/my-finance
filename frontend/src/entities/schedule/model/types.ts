export type ScheduleType = 'income' | 'expense' | 'transfer';

export interface RecurringSchedule {
  id: string;
  type: ScheduleType;
  name: string;
  amount: number;
  currency: string;
  schedule_day: number;
  start_date: string;
  end_date: string | null;
  total_count: number | null;
  executed_count: number;
  source_account_id: string | null;
  target_account_id: string | null;
  category_id: string | null;
  memo: string | null;
  is_active: boolean;
  created_at: string;
}

export interface ScheduleCreate {
  type: ScheduleType;
  name: string;
  amount: number;
  currency?: string;
  schedule_day: number;
  start_date: string;
  end_date?: string | null;
  total_count?: number | null;
  source_account_id?: string | null;
  target_account_id?: string | null;
  category_id?: string | null;
  memo?: string | null;
}

export interface ScheduleUpdate {
  name?: string | null;
  amount?: number | null;
  schedule_day?: number | null;
  end_date?: string | null;
  source_account_id?: string | null;
  target_account_id?: string | null;
  category_id?: string | null;
  memo?: string | null;
  is_active?: boolean | null;
}
