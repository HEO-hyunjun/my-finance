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
  news_refresh_interval: number;
  investment_prompt: string | null;
  asset_type_colors: Record<string, string> | null;
}

export interface AppSettingsUpdate {
  theme?: string | null;
  default_currency?: string | null;
  news_refresh_interval?: number | null;
  asset_type_colors?: Record<string, string> | null;
}
