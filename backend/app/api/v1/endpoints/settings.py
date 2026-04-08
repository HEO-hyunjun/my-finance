from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.settings import (
    ApiKeyCreate,
    ApiKeyResponse,
    LlmSettingUpdate,
    LlmSettingResponse,
    AppSettingsResponse,
    AppSettingsUpdate,
    InvestmentPromptUpdate,
    InvestmentPromptResponse,
)
from app.services import settings_service

router = APIRouter(tags=["settings"])


@router.get("", response_model=AppSettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await settings_service.get_app_settings(db, user)


@router.put("", response_model=AppSettingsResponse)
async def update_settings(
    data: AppSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await settings_service.update_app_settings(db, user, data)


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def get_api_keys(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await settings_service.get_api_keys(db, user.id)


@router.put("/api-keys", response_model=ApiKeyResponse)
async def upsert_api_key(
    data: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await settings_service.upsert_api_key(db, user.id, data)


@router.delete("/api-keys/{service}")
async def delete_api_key(
    service: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        await settings_service.delete_api_key(db, user.id, service)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid service type")
    return {"message": "API key deleted"}


@router.get("/llm", response_model=LlmSettingResponse)
async def get_llm(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await settings_service.get_llm_settings(db, user.id)


@router.put("/llm", response_model=LlmSettingResponse)
async def update_llm(
    data: LlmSettingUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await settings_service.update_llm_settings(db, user.id, data)


@router.get("/investment-prompt", response_model=InvestmentPromptResponse)
async def get_investment_prompt(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await settings_service.get_investment_prompt(db, user.id)


@router.put("/investment-prompt", response_model=InvestmentPromptResponse)
async def update_investment_prompt(
    data: InvestmentPromptUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await settings_service.update_investment_prompt(db, user.id, data.investment_prompt)


@router.delete("/investment-prompt")
async def delete_investment_prompt(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await settings_service.delete_investment_prompt(db, user.id)
    return {"message": "Investment prompt deleted"}
