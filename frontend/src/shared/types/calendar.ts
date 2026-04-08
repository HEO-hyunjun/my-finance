export interface CalendarEvent {
  date: string;
  type: string;
  title: string;
  amount: number;
  color: string;
  description: string | null;
  source_asset_name: string | null;
}

export interface DaySummary {
  date: string;
  total_amount: number;
  total_expense: number;
  total_income: number;
  event_count: number;
  event_types: string[];
}

export interface MonthSummary {
  year: number;
  month: number;
  total_scheduled_amount: number;
  total_expense_amount: number;
  total_income_amount: number;
  event_count: number;
  maturity_count: number;
  budget_period_start: string | null;
  budget_period_end: string | null;
}

export interface CalendarEventsResponse {
  events: CalendarEvent[];
  day_summaries: DaySummary[];
  month_summary: MonthSummary;
}
