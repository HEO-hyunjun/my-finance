import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.services.settings_service import authenticate_by_api_key

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    # 1) X-API-Key 헤더 확인
    api_key = request.headers.get("X-API-Key")
    if api_key:
        user = await authenticate_by_api_key(db, api_key)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        return user

    # 2) JWT Bearer 토큰 확인
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id or payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user = await db.get(User, uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user


async def get_current_user_jwt_only(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
) -> User:
    """JWT 전용 인증. API Key 관리 엔드포인트에서 사용."""
    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id or payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user = await db.get(User, uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user
