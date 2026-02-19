// 자산 유형
export type AssetType =
  | 'stock_kr' | 'stock_us' | 'gold' | 'cash_krw' | 'cash_usd'
  | 'deposit' | 'savings' | 'parking';

// 이자 유형
export type InterestType = 'simple' | 'compound';

// 거래 유형
export type TransactionType = 'buy' | 'sell' | 'exchange' | 'deposit' | 'withdraw' | 'transfer';

// 통화
export type CurrencyType = 'KRW' | 'USD';

// 사용자
export interface User {
  id: string;
  email: string;
  nickname: string;
  created_at: string;
}

// 자산 (DB 엔티티)
export interface Asset {
  id: string;
  asset_type: AssetType;
  symbol?: string;
  name: string;
  created_at: string;
  // 예금/적금/파킹통장 전용
  interest_rate?: number;
  interest_type?: InterestType;
  principal?: number;
  monthly_amount?: number;
  start_date?: string;
  maturity_date?: string;
  tax_rate?: number;
  bank_name?: string;
}

// 자산 생성 요청
export interface AssetCreateRequest {
  asset_type: AssetType;
  symbol?: string;
  name: string;
  // 예금/적금/파킹통장 전용
  interest_rate?: number;
  interest_type?: InterestType;
  principal?: number;
  monthly_amount?: number;
  start_date?: string;
  maturity_date?: string;
  tax_rate?: number;
  bank_name?: string;
  // 적금 자동이체 연동
  auto_transfer_source_id?: string;
  auto_transfer_day?: number;
}

export interface AssetUpdateRequest {
  name?: string;
  interest_rate?: number;
  interest_type?: InterestType;
  principal?: number;
  monthly_amount?: number;
  start_date?: string;
  maturity_date?: string;
  tax_rate?: number;
  bank_name?: string;
}

// 자산 보유 현황
export interface AssetHolding {
  id: string;
  asset_type: AssetType;
  symbol?: string;
  name: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  exchange_rate?: number;
  total_value_krw: number;
  total_invested_krw: number;
  profit_loss: number;
  profit_loss_rate: number;
  created_at: string;
  // 예금/적금/파킹통장 전용
  interest_rate?: number;
  interest_type?: InterestType;
  bank_name?: string;
  principal?: number;
  monthly_amount?: number;
  start_date?: string;
  maturity_date?: string;
  tax_rate?: number;
  accrued_interest_pretax?: number;
  accrued_interest_aftertax?: number;
  maturity_amount?: number;
  daily_interest?: number;
  monthly_interest?: number;
  elapsed_months?: number;
  total_months?: number;
  paid_count?: number;
  price_cached?: boolean;
}

// 자산 요약
export interface AssetSummary {
  total_value_krw: number;
  total_invested_krw: number;
  total_profit_loss: number;
  total_profit_loss_rate: number;
  breakdown: Record<string, number>;
  holdings: AssetHolding[];
}

// 거래 (응답)
export interface Transaction {
  id: string;
  asset_id: string;
  asset_name: string;
  asset_type: string;
  type: TransactionType;
  quantity: number;
  unit_price: number;
  currency: CurrencyType;
  exchange_rate?: number;
  fee: number;
  memo?: string;
  source_asset_id?: string;
  source_asset_name?: string;
  transacted_at: string;
  created_at: string;
}

// 거래 생성 요청
export interface TransactionCreateRequest {
  asset_id: string;
  type: TransactionType;
  quantity: number;
  unit_price: number;
  currency: CurrencyType;
  exchange_rate?: number;
  fee?: number;
  memo?: string;
  transacted_at: string;
  source_asset_id?: string;
}

// 거래 수정 요청
export interface TransactionUpdateRequest {
  type?: TransactionType;
  quantity?: number;
  unit_price?: number;
  currency?: CurrencyType;
  exchange_rate?: number;
  fee?: number;
  memo?: string;
  transacted_at?: string;
}

// 시세 정보
export interface PriceInfo {
  symbol: string;
  name?: string;
  price: number;
  currency: string;
  change?: number;
  change_percent?: number;
  is_market_open: boolean;
  cached: boolean;
}

// 환율 정보
export interface ExchangeRate {
  pair: string;
  rate: number;
  change?: number;
  change_percent?: number;
  cached: boolean;
}

// 결제수단
export type PaymentMethod = 'cash' | 'card' | 'transfer';

// 예산 카테고리
export interface BudgetCategory {
  id: string;
  name: string;
  icon?: string;
  color?: string;
  monthly_budget: number;
  sort_order: number;
  is_active: boolean;
  created_at: string;
}

export interface BudgetCategoryCreateRequest {
  name: string;
  icon?: string;
  color?: string;
  monthly_budget?: number;
  sort_order?: number;
}

export interface BudgetCategoryUpdateRequest {
  name?: string;
  icon?: string;
  color?: string;
  monthly_budget?: number;
  sort_order?: number;
  is_active?: boolean;
}

// 지출
export interface Expense {
  id: string;
  category_id: string;
  category_name: string;
  category_color?: string;
  amount: number;
  memo?: string;
  tags?: string;
  source_asset_id?: string;
  source_asset_name?: string;
  spent_at: string;
  created_at: string;
}

export interface ExpenseCreateRequest {
  category_id: string;
  amount: number;
  memo?: string;
  tags?: string;
  spent_at: string;
  source_asset_id?: string;
}

export interface ExpenseUpdateRequest {
  category_id?: string;
  amount?: number;
  memo?: string;
  tags?: string;
  spent_at?: string;
  source_asset_id?: string;
}

// 예산 요약
export interface CategoryBudgetSummary {
  category_id: string;
  category_name: string;
  category_icon?: string;
  category_color?: string;
  monthly_budget: number;
  spent: number;
  remaining: number;
  usage_rate: number;
}

export interface BudgetSummaryResponse {
  period_start: string;
  period_end: string;
  total_budget: number;
  total_spent: number;
  total_remaining: number;
  total_usage_rate: number;
  categories: CategoryBudgetSummary[];
  // Phase 2
  total_fixed_expenses: number;
  total_installments: number;
  variable_budget: number;
  variable_spent: number;
  variable_remaining: number;
}

// 고정비
export interface FixedExpense {
  id: string;
  category_id: string;
  category_name: string;
  category_color?: string;
  name: string;
  amount: number;
  payment_day: number;
  source_asset_id?: string;
  source_asset_name?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface FixedExpenseCreateRequest {
  category_id: string;
  name: string;
  amount: number;
  payment_day: number;
  source_asset_id?: string;
}

export interface FixedExpenseUpdateRequest {
  category_id?: string;
  name?: string;
  amount?: number;
  payment_day?: number;
  source_asset_id?: string;
  is_active?: boolean;
}

// 할부금
export interface Installment {
  id: string;
  category_id: string;
  category_name: string;
  category_color?: string;
  name: string;
  total_amount: number;
  monthly_amount: number;
  payment_day: number;
  total_installments: number;
  paid_installments: number;
  remaining_installments: number;
  remaining_amount: number;
  progress_rate: number;
  start_date: string;
  end_date: string;
  source_asset_id?: string;
  source_asset_name?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface InstallmentCreateRequest {
  category_id: string;
  name: string;
  total_amount: number;
  monthly_amount: number;
  payment_day: number;
  total_installments: number;
  start_date: string;
  end_date: string;
  source_asset_id?: string;
}

export interface InstallmentUpdateRequest {
  category_id?: string;
  name?: string;
  monthly_amount?: number;
  payment_day?: number;
  source_asset_id?: string;
  is_active?: boolean;
}

// 결제수단 라벨
export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  cash: '현금',
  card: '카드',
  transfer: '이체',
};

// API 응답 공통
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
}

// 자산 유형 라벨
export const ASSET_TYPE_LABELS: Record<AssetType, string> = {
  stock_kr: '국내주식',
  stock_us: '미국주식',
  gold: '금',
  cash_krw: '원화',
  cash_usd: '달러',
  deposit: '예금',
  savings: '적금',
  parking: '파킹통장',
};

// 거래 유형 라벨
export const TRANSACTION_TYPE_LABELS: Record<TransactionType, string> = {
  buy: '매수',
  sell: '매도',
  exchange: '환전',
  deposit: '입금',
  withdraw: '출금',
  transfer: '이체',
};

// ========== Dashboard Types ==========

export interface DashboardAssetSummary {
  total_value_krw: number;
  total_invested_krw: number;
  total_profit_loss: number;
  total_profit_loss_rate: number;
  breakdown: Record<string, number>;
}

export interface DashboardBudgetCategory {
  name: string;
  icon?: string;
  color?: string;
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
  name?: string;
  price: number;
  currency: string;
  change?: number;
  change_percent?: number;
}

export interface DashboardMarketInfo {
  exchange_rate: DashboardMarketItem;
  gold_price?: DashboardMarketItem;
}

export interface DashboardPayment {
  name: string;
  amount: number;
  payment_day: number;
  type: 'fixed' | 'installment';
  remaining?: string;
  category_name?: string;
  category_color?: string;
}

export interface DashboardMaturityAlert {
  name: string;
  asset_type: string;
  maturity_date: string;
  principal: number;
  maturity_amount?: number;
  days_remaining: number;
  bank_name?: string;
}

export interface DashboardSummaryResponse {
  asset_summary: DashboardAssetSummary;
  budget_summary: DashboardBudgetSummary;
  recent_transactions: DashboardTransaction[];
  market_info: DashboardMarketInfo;
  upcoming_payments: DashboardPayment[];
  maturity_alerts: DashboardMaturityAlert[];
}

// ========== News Types ==========

export interface NewsSource {
  name: string;
  icon?: string;
}

export interface NewsArticle {
  id: string;
  title: string;
  link: string;
  source: NewsSource;
  snippet?: string;
  thumbnail?: string;
  published_at: string;
  category: string;
  related_asset?: string;
}

export interface NewsListResponse {
  articles: NewsArticle[];
  page: number;
  per_page: number;
  has_next: boolean;
}

export interface MyAssetNewsResponse {
  articles: NewsArticle[];
  asset_queries: string[];
}

export type NewsCategory = 'all' | 'my_assets' | 'stock_kr' | 'stock_us' | 'gold' | 'economy';

// ========== Calendar Types ==========

export type CalendarEventType = 'fixed_expense' | 'installment' | 'maturity' | 'expense' | 'income';

export interface CalendarEvent {
  date: string;
  type: CalendarEventType;
  title: string;
  amount: number;
  color: string;
  description?: string;
  source_asset_name?: string;
}

export interface DaySummary {
  date: string;
  total_amount: number;
  total_expense: number;
  total_income: number;
  event_count: number;
  event_types: CalendarEventType[];
}

export interface MonthSummary {
  year: number;
  month: number;
  total_scheduled_amount: number;
  total_expense_amount: number;
  total_income_amount: number;
  event_count: number;
  maturity_count: number;
}

export interface CalendarEventsResponse {
  events: CalendarEvent[];
  day_summaries: DaySummary[];
  month_summary: MonthSummary;
}

// ========== Chatbot Types ==========

export type ChatMessageRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  created_at: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  last_message_at: string | null;
  message_count: number;
}

export interface ConversationListResponse {
  conversations: ConversationSummary[];
}

export interface ConversationDetailResponse {
  id: string;
  title: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string | null;
}

export interface ChatTokenEvent {
  type: 'token';
  content: string;
}

export interface ChatDoneEvent {
  type: 'done';
  conversation_id: string;
  message_id: string;
}

export interface ChatErrorEvent {
  type: 'error';
  message: string;
}

export type ChatSSEEvent = ChatTokenEvent | ChatDoneEvent | ChatErrorEvent;

// ========== Settings Types ==========

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  default_currency: string;
  salary_day: number;
  salary_asset_id?: string;
  salary_asset_name?: string;
  salary_amount?: number;
  notification_preferences: NotificationPreferences | null;
  created_at: string;
  updated_at: string;
}

export interface ProfileUpdateRequest {
  name?: string;
  default_currency?: string;
  salary_day?: number;
  salary_asset_id?: string | null;
  salary_amount?: number | null;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

export interface NotificationPreferences {
  budget_alert: boolean;
  maturity_alert: boolean;
  market_alert: boolean;
  email_notifications: boolean;
}

export interface AccountDeleteRequest {
  password: string;
}

// ========== Income Types ==========

export type IncomeType = 'salary' | 'side' | 'investment' | 'other';

export const INCOME_TYPE_LABELS: Record<IncomeType, string> = {
  salary: '급여',
  side: '부수입',
  investment: '투자수익',
  other: '기타',
};

export interface Income {
  id: string;
  type: IncomeType;
  amount: number;
  description: string;
  is_recurring: boolean;
  recurring_day?: number;
  target_asset_id?: string;
  target_asset_name?: string;
  received_at: string;
  created_at: string;
}

export interface IncomeCreateRequest {
  type: IncomeType;
  amount: number;
  description: string;
  is_recurring?: boolean;
  recurring_day?: number;
  received_at: string;
  target_asset_id?: string;
}

export interface IncomeUpdateRequest {
  type?: IncomeType;
  amount?: number;
  description?: string;
  is_recurring?: boolean;
  recurring_day?: number;
  received_at?: string;
  target_asset_id?: string;
}

export interface IncomeSummary {
  total_monthly_income: number;
  salary_income: number;
  side_income: number;
  investment_income: number;
  other_income: number;
  recurring_count: number;
}

// ========== Carryover Types ==========

export type CarryoverType = 'expire' | 'next_month' | 'savings' | 'transfer' | 'deposit';

export const CARRYOVER_TYPE_LABELS: Record<CarryoverType, string> = {
  expire: '소멸',
  next_month: '다음달 이월',
  savings: '저축 이동',
  transfer: '단순 이체',
  deposit: '예금 이동',
};

export interface CarryoverSetting {
  id: string;
  category_id: string;
  category_name: string;
  carryover_type: CarryoverType;
  carryover_limit?: number;
  target_asset_id?: string;
  target_savings_name?: string;
  target_annual_rate?: number;
  created_at: string;
  updated_at: string;
}

export interface CarryoverSettingRequest {
  category_id: string;
  carryover_type: CarryoverType;
  carryover_limit?: number;
  target_asset_id?: string;
  target_savings_name?: string;
  target_annual_rate?: number;
}

export interface CarryoverLog {
  id: string;
  category_id: string;
  category_name: string;
  budget_period_start: string;
  budget_period_end: string;
  carryover_type: CarryoverType;
  amount: number;
  target_description?: string;
  executed_at: string;
  created_at: string;
}

export interface CarryoverPreview {
  category_id: string;
  category_name: string;
  carryover_type: CarryoverType;
  budget: number;
  spent: number;
  remaining: number;
  carryover_amount: number;
  target_description?: string;
}

// ========== Portfolio Types ==========

export interface AssetSnapshot {
  id: string;
  snapshot_date: string;
  total_krw: number;
  breakdown: Record<string, number>;
  created_at: string;
}

export interface AssetTimeline {
  snapshots: AssetSnapshot[];
  period: string;
  start_date: string;
  end_date: string;
}

export interface GoalAsset {
  id: string;
  target_amount: number;
  target_date?: string;
  current_amount: number;
  achievement_rate: number;
  remaining_amount: number;
  monthly_required?: number;
  estimated_date?: string;
  created_at: string;
  updated_at: string;
}

export interface GoalAssetRequest {
  target_amount: number;
  target_date?: string;
}

export interface PortfolioTarget {
  id: string;
  asset_type: string;
  target_ratio: number;
  current_ratio: number;
  deviation: number;
  created_at: string;
  updated_at: string;
}

export interface PortfolioTargetRequest {
  asset_type: string;
  target_ratio: number;
}

export interface RebalancingSuggestion {
  asset_type: string;
  action: 'buy' | 'sell';
  amount_krw: number;
  deviation: number;
}

export interface RebalancingAnalysis {
  targets: PortfolioTarget[];
  total_deviation: number;
  needs_rebalancing: boolean;
  threshold: number;
  suggestions: RebalancingSuggestion[];
}

export interface RebalancingAlert {
  id: string;
  snapshot_date: string;
  deviations: Record<string, number>;
  suggestion: Record<string, unknown>;
  threshold: number;
  is_read: boolean;
  created_at: string;
}

// ── Settings ──

export type ApiServiceType = 'tavily' | 'serpapi' | 'openai' | 'anthropic' | 'google' | 'mistral' | 'custom_llm';

export const API_SERVICE_LABELS: Record<ApiServiceType, string> = {
  tavily: 'Tavily',
  serpapi: 'SerpAPI',
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  google: 'Google',
  mistral: 'Mistral',
  custom_llm: 'Custom LLM',
};

export interface ApiKeyInfo {
  service: ApiServiceType;
  is_set: boolean;
  masked_key: string | null;
  updated_at: string | null;
}

export interface ApiKeyCreateRequest {
  service: ApiServiceType;
  api_key: string;
}

export interface LlmSettings {
  default_model: string;
  inference_model: string;
  updated_at: string | null;
}

export interface LlmSettingsUpdateRequest {
  default_model?: string;
  inference_model?: string;
}

export type ThemeMode = 'light' | 'dark' | 'system';

export interface AppSettings {
  api_keys: ApiKeyInfo[];
  llm: LlmSettings;
  theme: ThemeMode;
  default_currency: string;
  news_refresh_interval: number;
}

export interface AppSettingsUpdateRequest {
  theme?: ThemeMode;
  default_currency?: string;
  news_refresh_interval?: number;
}

export interface InvestmentPromptResponse {
  investment_prompt: string | null;
  updated_at: string | null;
}

// ========== AI Insights ==========

export type InsightType = 'spending' | 'budget' | 'investment' | 'saving' | 'alert';
export type InsightSeverity = 'info' | 'warning' | 'success';

export interface AIInsight {
  type: InsightType;
  title: string;
  description: string;
  severity: InsightSeverity;
}

export interface AIInsightsResponse {
  insights: AIInsight[];
}

// ========== News Cluster ==========

export interface ProcessedNewsArticle {
  id: string;
  external_id: string;
  title: string;
  link: string;
  source_name: string;
  snippet?: string;
  thumbnail?: string;
  published_at: string;
  category: string;
  summary?: string;
  sentiment?: string;
  sentiment_score?: number;
  keywords?: string;
}

export interface NewsCluster {
  id: string;
  title: string;
  summary: string;
  category: string;
  sentiment: string;
  avg_sentiment_score: number;
  article_count: number;
  keywords: string[];
  importance_score: number;
  created_at: string;
}

// ========== Transfer Types ==========

export interface TransferRequest {
  source_asset_id: string;
  target_asset_id: string;
  amount: number;
  exchange_rate?: number;
  memo?: string;
  transacted_at?: string;
}

export interface AutoTransfer {
  id: string;
  name: string;
  source_asset_id: string;
  source_asset_name?: string;
  target_asset_id: string;
  target_asset_name?: string;
  amount: number;
  transfer_day: number;
  is_active: boolean;
  created_at?: string;
}

export interface AutoTransferCreateRequest {
  source_asset_id: string;
  target_asset_id: string;
  name: string;
  amount: number;
  transfer_day: number;
}

export interface NewsClustersResponse {
  clusters: NewsCluster[];
}

// ── Budget Analysis ──

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
}

export interface FixedDeductionSummary {
  items: FixedDeductionItem[];
  total_amount: number;
  paid_amount: number;
  remaining_amount: number;
}

export interface CarryoverPredictionItem {
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
  carryover_predictions: CarryoverPredictionItem[];
  alerts: string[];
}
