import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# --- API Keys ---

class ApiKeyCreate(BaseModel):
    service: str = Field(pattern=r"^(tavily|serpapi|openai|anthropic|google|mistral|custom_llm)$")
    api_key: str = Field(min_length=1, max_length=500)


class ApiKeyResponse(BaseModel):
    service: str
    is_set: bool
    masked_key: str | None = None
    updated_at: datetime | None = None


class ApiKeyBulkUpdate(BaseModel):
    keys: list[ApiKeyCreate]


# --- LLM Settings ---

class LlmSettingUpdate(BaseModel):
    default_model: str | None = Field(default=None, max_length=100)
    inference_model: str | None = Field(default=None, max_length=100)


class LlmSettingResponse(BaseModel):
    default_model: str
    inference_model: str
    updated_at: datetime | None = None


# --- Investment Prompt ---

class InvestmentPromptUpdate(BaseModel):
    investment_prompt: str = Field(max_length=2000)


class InvestmentPromptResponse(BaseModel):
    investment_prompt: str | None = None
    updated_at: datetime | None = None


# --- Combined Settings ---

class AppSettingsResponse(BaseModel):
    api_keys: list[ApiKeyResponse]
    llm: LlmSettingResponse
    theme: str  # "light" | "dark" | "system"
    default_currency: str
    news_refresh_interval: int  # minutes
    investment_prompt: str | None = None
    salary_asset_id: uuid.UUID | None = None
    salary_asset_name: str | None = None
    asset_type_colors: dict[str, str] | None = None


class AppSettingsUpdate(BaseModel):
    theme: str | None = Field(default=None, pattern=r"^(light|dark|system)$")
    default_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    news_refresh_interval: int | None = Field(default=None, ge=5, le=1440)
    salary_asset_id: uuid.UUID | None = None
    asset_type_colors: dict[str, str] | None = None
