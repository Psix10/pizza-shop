from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import JWTError, jwt


class TokenService:
    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str,
        access_token_expire_minutes: int,
        refresh_token_expire_days: int,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    # ====== Универсальные методы ======

    def create_access_token_generic(
        self,
        *,
        subject: str,
        role: str | None = None,
        principal_type: str | None = None,  # "admin" или "user"
        issuer: str = "auth_service",
        audience: str | None = "internal_api",
        token_type: str = "access",
        custom_claims: dict | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        to_encode: dict = {
            "sub": subject,
            "iss": issuer,
            "type": token_type,
            "iat": now,
            "exp": expire,
        }
        if audience is not None:
            to_encode["aud"] = audience
        if role is not None:
            to_encode["role"] = role
        if principal_type is not None:
            to_encode["principal_type"] = principal_type
        if custom_claims:
            to_encode.update(custom_claims)

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token_generic(
        self,
        *,
        subject: str,
        issuer: str = "auth_service",
        token_type: str = "refresh",
    ) -> tuple[str, datetime]:
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_token_expire_days)

        payload = {
            "sub": subject,
            "iss": issuer,
            "type": token_type,
            "iat": now,
            "exp": expire,
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, expire

    def decode_token(self, token: str) -> dict:
        try:
            return jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_aud": False},
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

    def require_token_type(self, payload: dict, token_type: str) -> None:
        actual_type = payload.get("type")
        if actual_type != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type: expected {token_type}",
            )

    # ====== Старые admin-методы для обратной совместимости ======

    def create_access_token(self, payload: dict) -> str:
        """
        Старый метод, используется админкой.
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        to_encode = payload.copy()
        to_encode.update(
            {
                "iss": "admin_service",
                "aud": "internal_api",
                "type": "access",
                "token_type": "admin_access",
                "iat": now,
                "exp": expire,
            }
        )
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, admin_id: int) -> tuple[str, datetime]:
        """
        Старый метод, используется админкой.
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_token_expire_days)

        payload = {
            "sub": str(admin_id),
            "iss": "admin_service",
            "type": "refresh",
            "token_type": "admin_refresh",
            "iat": now,
            "exp": expire,
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, expire