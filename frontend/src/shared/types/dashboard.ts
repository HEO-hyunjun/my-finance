export interface DashboardAssetSummary {
  total_value_krw: number;
  total_invested_krw: number;
  total_profit_loss: number;
  total_profit_loss_rate: number;
  daily_change: number | null;
  daily_change_rate: number | null;
  breakdown: Record<string, number>;
}

export interface DashboardBudgetCategory {
  name: string;
  icon: string | null;
  color: string | null;
  budget: number;
  spent: number;
  usage_rate: number;
}

export interface DashboardBudgetSummary {
  total_budget: number;
  total_spent: number;
  total_remaining: number;
  total_usage_rate: number;
  total_fixed_expenses: number;
  total_installments: number;
  daily_available: number;
  today_spent: number;
  remaining_days: number;
  top_categories: DashboardBudgetCategory[];
}

export interface DashboardTransaction {
  id: string;
  asset_name: string;
  asset_type: string;
  type: string;
  quantity: number;
  unit_price: number;
  currency: string;
  transacted_at: string;
}

export interface DashboardMarketItem {
  symbol: string;
  name: string | null;
  price: number;
  currency: string;
  change: number | null;
  change_percent: number | null;
}

export interface DashboardMarketInfo {
  exchange_rate: DashboardMarketItem;
  gold_price: DashboardMarketItem | null;
}

export interface DashboardPayment {
  name: string;
  amount: number;
  payment_day: number;
  type: string;
  remaining: string | null;
  category_name: string | null;
  category_color: string | null;
}

export interface DashboardMaturityAlert {
  name: string;
  asset_type: string;
  maturity_date: string;
  principal: number;
  maturity_amount: number | null;
  days_remaining: number;
  bank_name: string | null;
}

export interface DashboardSummaryResponse {
  asset_summary: DashboardAssetSummary;
  budget_summary: DashboardBudgetSummary;
  recent_transactions: DashboardTransaction[];
  market_info: DashboardMarketInfo;
  upcoming_payments: DashboardPayment[];
  maturity_alerts: DashboardMaturityAlert[];
}

export interface AIInsight {
  type: 'spending' | 'budget' | 'investment' | 'saving' | 'alert';
  title: string;
  description: string;
  severity: 'info' | 'warning' | 'success';
  generated_at: string | null;
}

export interface AIInsightsResponse {
  insights: AIInsight[];
}
