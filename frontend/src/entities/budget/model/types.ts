export interface BudgetOverview {
  period_start: string;
  period_end: string;
  period_start_day: number;
  total_income: number;
  total_fixed_expense: number;
  total_transfer: number;
  available_budget: number;
  total_allocated: number;
  unallocated: number;
}

export interface CategoryBudget {
  allocation_id: string;
  category_id: string;
  allocated: number;
  spent: number;
  remaining: number;
}

export interface AllocationCreate {
  category_id: string;
  amount: number;
}

export interface AllocationUpdate {
  amount: number;
}

export interface PeriodSettingUpdate {
  period_start_day: number;
}

export interface DailyBudget {
  daily_available: number;
  remaining_budget: number;
  remaining_days: number;
  today_spent: number;
  period_start: string;
  period_end: string;
}

export interface WeeklyAnalysis {
  week_start: string;
  week_end: string;
  week_spent: number;
  weekly_average_budget: number;
  usage_rate: number;
  is_over_budget: boolean;
}

export interface CategorySpendingRate {
  category_id: string;
  category_name: string;
  category_icon: string;
  category_color: string;
  monthly_budget: number;
  spent: number;
  remaining: number;
  usage_rate: number;
  status: 'normal' | 'warning' | 'exceeded';
}

export interface FixedDeductionItem {
  name: string;
  amount: number;
  payment_day: number;
  is_paid: boolean;
  item_type: 'fixed' | 'installment';
  color?: string;
}

export interface FixedDeductionSummary {
  items: FixedDeductionItem[];
  total_amount: number;
  paid_amount: number;
  remaining_amount: number;
}

export interface CarryoverPrediction {
  category_id: string;
  category_name: string;
  predicted_remaining: number;
  carryover_type: string | null;
  predicted_carryover: number;
}

export interface BudgetAnalysis {
  daily_budget: DailyBudget;
  weekly_analysis: WeeklyAnalysis;
  category_rates: CategorySpendingRate[];
  fixed_deductions: FixedDeductionSummary;
  carryover_predictions: CarryoverPrediction[];
  alerts: string[];
}
