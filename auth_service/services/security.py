# core/security.py
import os

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.db import get_session
from models.user import User
from services.token_service import TokenService  # где ты создаёшь его экземпляр


JWT_SECRET_KEY = os.getenv("USER_JWT_SECRET_KEY", "dev-secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


token_service = TokenService(
    secret_key=JWT_SECRET_KEY,
    algorithm=JWT_ALGORITHM,
    access_token_expire_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
    refresh_token_expire_days=REFRESH_TOKEN_EXPIRE_DAYS,
)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: AsyncSession = Depends(get_session),
) -> User:
    payload = token_service.decode_token(token)
    token_service.require_token_type(payload, "access")

    sub: str | None = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    stmt = select(User).where(User.id == int(sub))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user