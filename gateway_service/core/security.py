# core/security.py
import os
from typing import Any

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

def decode_jwt_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"verify_aud": False},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

PUBLIC_PATHS = {
    "/api/auth/register/customer",
    "/api/auth/login",
    "/api/auth/refresh",
    "/api/auth/logout",
    "/api/profile/me",
    "/api/profile/addresses",
    "/api/profile/contacts",
}
PUBLIC_PREFIXES = {
    "/api/docs",
    "/api/openapi.json",
    "/api/catalog",
    "/api/stores",
}

def is_public_path(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)

async def get_auth_context(request: Request) -> dict[str, Any] | None:
    path = request.url.path

    if is_public_path(path):
        return None

    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    token = auth_header.split(" ", 1)[1].strip()
    payload = decode_jwt_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token required",
        )

    if payload.get("principal_type") not in ("user", None):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User token required",
        )

    if not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    return payload