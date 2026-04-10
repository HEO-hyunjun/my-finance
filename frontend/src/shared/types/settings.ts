export interface ApiKeyCreate { service: string; api_key: string; }

export interface ApiKeyResponse {
  service: string;
  is_set: boolean;
  masked_key: string | null;
  updated_at: string | null;
}

export interface LlmSettingUpdate { default_model?: string | null; inference_model?: string | null; }

export interface LlmSettingResponse {
  default_model: string;
  inference_model: string;
  updated_at: string | null;
}

export interface InvestmentPromptUpdate { investment_prompt: string; }
export interface InvestmentPromptResponse { investment_prompt: string | null; updated_at: string | null; }

export interface AppSettingsResponse {
  api_keys: ApiKeyResponse[];
  llm: LlmSettingResponse;
  theme: string;
  default_currency: string;
  investment_prompt: string | null;
  asset_type_colors: Record<string, string> | null;
  dashboard_widgets: Record<string, boolean> | null;
}

export interface AppSettingsUpdate {
  theme?: string | null;
  default_currency?: string | null;
  asset_type_colors?: Record<string, string> | null;
  dashboard_widgets?: Record<string, boolean> | null;
}

// Backwards-compatible aliases (legacy names)
export type AppSettings = AppSettingsResponse;
export type AppSettingsUpdateRequest = AppSettingsUpdate;
export type ApiKeyCreateRequest = ApiKeyCreate;
export type ApiKeyInfo = ApiKeyResponse;
export type LlmSettings = LlmSettingResponse;
export type LlmSettingsUpdateRequest = LlmSettingUpdate;

export type ThemeMode = 'light' | 'dark' | 'system';
export type ApiServiceType = string;
export const API_SERVICE_LABELS: Record<string, string> = {
  serpapi: 'SerpAPI',
  openai: 'OpenAI',
};

export interface RecurringIncome {
  id: string;
  name: string;
  amount: number;
  currency: string;
  day: number;
  is_active: boolean;
  income_type: string;
  asset_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface RecurringIncomeCreateRequest {
  name: string;
  amount: number;
  currency?: string;
  day: number;
  income_type: string;
  asset_id?: string | null;
}

export interface RecurringIncomeUpdateRequest {
  name?: string;
  amount?: number;
  currency?: string;
  day?: number;
  income_type?: string;
  asset_id?: string | null;
}

export interface IncomeSummary {
  total_income: number;
  incomes: Array<{ name: string; amount: number; currency: string; income_type: string }>;
}

export type IncomeType = string;
export const INCOME_TYPE_LABELS: Record<string, string> = {
  salary: '급여',
  bonus: '보너스',
  dividend: '배당금',
  interest: '이자',
  rental: '임대수입',
  other: '기타',
};

// --- Personal API Key ---

export interface PersonalApiKeyStatus {
  is_set: boolean;
  prefix: string | null;
  created_at: string | null;
}

export interface PersonalApiKeyCreated {
  api_key: string;
  prefix: string;
  created_at: string;
}

export interface PersonalApiKeyRevealed {
  api_key: string;
}
