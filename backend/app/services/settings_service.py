import uuid
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.settings import ApiKey, ApiServiceType, LlmSetting
from app.models.user import User
from app.schemas.settings import (
    ApiKeyCreate,
    ApiKeyResponse,
    LlmSettingResponse,
    LlmSettingUpdate,
    AppSettingsResponse,
    AppSettingsUpdate,
    InvestmentPromptResponse,
)


def _get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY
    if not key:
        key = Fernet.generate_key().decode()
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def _encrypt(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    return _get_fernet().decrypt(value.encode()).decode()


def _mask_key(key: str) -> str:
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


ALL_SERVICES = [s.value for s in ApiServiceType]


async def get_api_keys(
    db: AsyncSession, user_id: uuid.UUID
) -> list[ApiKeyResponse]:
    stmt = select(ApiKey).where(ApiKey.user_id == user_id)
    result = await db.execute(stmt)
    stored = {k.service.value: k for k in result.scalars().all()}

    responses = []
    for svc in ALL_SERVICES:
        if svc in stored:
            key_obj = stored[svc]
            try:
                raw = _decrypt(key_obj.encrypted_key)
                masked = _mask_key(raw)
            except Exception:
                masked = "****"
            responses.append(ApiKeyResponse(
                service=svc,
                is_set=True,
                masked_key=masked,
                updated_at=key_obj.updated_at,
            ))
        else:
            responses.append(ApiKeyResponse(
                service=svc,
                is_set=False,
                masked_key=None,
                updated_at=None,
            ))
    return responses


async def upsert_api_key(
    db: AsyncSession, user_id: uuid.UUID, data: ApiKeyCreate
) -> ApiKeyResponse:
    service_enum = ApiServiceType(data.service)
    stmt = select(ApiKey).where(
        ApiKey.user_id == user_id,
        ApiKey.service == service_enum,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    encrypted = _encrypt(data.api_key)

    if existing:
        existing.encrypted_key = encrypted
        existing.updated_at = datetime.now(timezone.utc)
    else:
        existing = ApiKey(
            user_id=user_id,
            service=service_enum,
            encrypted_key=encrypted,
        )
        db.add(existing)

    await db.commit()
    await db.refresh(existing)

    return ApiKeyResponse(
        service=data.service,
        is_set=True,
        masked_key=_mask_key(data.api_key),
        updated_at=existing.updated_at,
    )


async def delete_api_key(
    db: AsyncSession, user_id: uuid.UUID, service: str
) -> None:
    service_enum = ApiServiceType(service)
    stmt = select(ApiKey).where(
        ApiKey.user_id == user_id,
        ApiKey.service == service_enum,
    )
    key_obj = (await db.execute(stmt)).scalar_one_or_none()
    if key_obj:
        await db.delete(key_obj)
        await db.commit()


async def get_decrypted_api_key(
    db: AsyncSession, user_id: uuid.UUID, service: str
) -> str | None:
    service_enum = ApiServiceType(service)
    stmt = select(ApiKey).where(
        ApiKey.user_id == user_id,
        ApiKey.service == service_enum,
    )
    key_obj = (await db.execute(stmt)).scalar_one_or_none()
    if not key_obj:
        return None
    try:
        return _decrypt(key_obj.encrypted_key)
    except Exception:
        return None


# --- LLM Settings ---


async def get_llm_settings(
    db: AsyncSession, user_id: uuid.UUID
) -> LlmSettingResponse:
    stmt = select(LlmSetting).where(LlmSetting.user_id == user_id)
    llm = (await db.execute(stmt)).scalar_one_or_none()

    if not llm:
        return LlmSettingResponse(
            default_model="gpt-4o",
            inference_model="gpt-4o",
            updated_at=None,
        )

    return LlmSettingResponse(
        default_model=llm.default_model,
        inference_model=llm.inference_model,
        updated_at=llm.updated_at,
    )


async def update_llm_settings(
    db: AsyncSession, user_id: uuid.UUID, data: LlmSettingUpdate
) -> LlmSettingResponse:
    stmt = select(LlmSetting).where(LlmSetting.user_id == user_id)
    llm = (await db.execute(stmt)).scalar_one_or_none()

    if not llm:
        llm = LlmSetting(
            user_id=user_id,
            default_model=data.default_model or "gpt-4o",
            inference_model=data.inference_model or "gpt-4o",
        )
        db.add(llm)
    else:
        if data.default_model is not None:
            llm.default_model = data.default_model
        if data.inference_model is not None:
            llm.inference_model = data.inference_model
        llm.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(llm)

    return LlmSettingResponse(
        default_model=llm.default_model,
        inference_model=llm.inference_model,
        updated_at=llm.updated_at,
    )


# --- Investment Prompt ---


async def get_investment_prompt(
    db: AsyncSession, user_id: uuid.UUID
) -> InvestmentPromptResponse:
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        return InvestmentPromptResponse()

    return InvestmentPromptResponse(
        investment_prompt=user.investment_prompt,
        updated_at=user.updated_at if user.investment_prompt else None,
    )


async def update_investment_prompt(
    db: AsyncSession, user_id: uuid.UUID, prompt: str
) -> InvestmentPromptResponse:
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one()

    user.investment_prompt = prompt
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    return InvestmentPromptResponse(
        investment_prompt=user.investment_prompt,
        updated_at=user.updated_at,
    )


async def delete_investment_prompt(
    db: AsyncSession, user_id: uuid.UUID
) -> None:
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one()

    user.investment_prompt = None
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()


# --- Combined Settings ---


async def get_app_settings(
    db: AsyncSession, user: User
) -> AppSettingsResponse:
    api_keys = await get_api_keys(db, user.id)
    llm = await get_llm_settings(db, user.id)

    prefs = user.notification_preferences or {}

    return AppSettingsResponse(
        api_keys=api_keys,
        llm=llm,
        theme=prefs.get("theme", "light"),
        default_currency=user.default_currency,
        news_refresh_interval=prefs.get("news_refresh_interval", 30),
        investment_prompt=user.investment_prompt,
        asset_type_colors=prefs.get("asset_type_colors"),
    )


async def update_app_settings(
    db: AsyncSession, user: User, data: AppSettingsUpdate
) -> AppSettingsResponse:
    prefs = dict(user.notification_preferences or {})

    if data.theme is not None:
        prefs["theme"] = data.theme
    if data.default_currency is not None:
        user.default_currency = data.default_currency
    if data.news_refresh_interval is not None:
        prefs["news_refresh_interval"] = data.news_refresh_interval
    if data.asset_type_colors is not None:
        prefs["asset_type_colors"] = data.asset_type_colors

    user.notification_preferences = prefs
    await db.commit()
    await db.refresh(user)

    return await get_app_settings(db, user)
