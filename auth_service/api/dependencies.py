# api/dependencies.py (user-часть)

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from db.db import get_session
from dao.user_dao import UserDAO
from models.user import User
from services.user_auth_service import UserAuthService
from services.password_service import PasswordService
from services.token_service import TokenService

# если bearer_scheme уже определён выше (для админов) — эту строку не дублируй
bearer_scheme = HTTPBearer(auto_error=False)


def get_password_service() -> PasswordService:
    # если такая функция уже есть в файле (для админов), вторую не добавляй
    return PasswordService()


def get_token_service() -> TokenService:
    # аналогично: если уже есть admin-версия с env-переменными, используй её
    import os

    return TokenService(
        secret_key=os.getenv("JWT_SECRET_KEY", "dev-secret"),
        algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        ),
        refresh_token_expire_days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")),
    )


def get_user_dao(session: AsyncSession = Depends(get_session)) -> UserDAO:
    return UserDAO(session)


def get_user_auth_service(
    dao: UserDAO = Depends(get_user_dao),
    token_service: TokenService = Depends(get_token_service),
    password_service: PasswordService = Depends(get_password_service),
) -> UserAuthService:
    return UserAuthService(
        dao=dao,
        token_service=token_service,
        password_service=password_service,
    )


async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    token_service: TokenService = Depends(get_token_service),
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
        )

    token = credentials.credentials
    payload = token_service.decode_token(token)
    token_service.require_token_type(payload, "access")

    principal_type = payload.get("principal_type")
    if principal_type not in ("user", None):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User token required",
        )

    if payload.get("sub") is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    return payload


async def get_current_user(
    payload: dict[str, Any] = Depends(get_current_user_payload),
    session: AsyncSession = Depends(get_session),
) -> User:
    user_id = int(payload["sub"])
    dao = UserDAO(session)
    user = await dao.get_user_by_id(user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user

