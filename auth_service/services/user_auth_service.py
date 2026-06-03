# services/user_auth_service.py
from datetime import datetime, timezone
import secrets

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from dao.user_dao import UserDAO
from services.password_service import PasswordService
from services.token_service import TokenService
from schemas.auth import (
    RegisterCustomerRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    LogoutRequest,
)
from models.role import Role


class UserAuthService:
    def __init__(
        self,
        dao: UserDAO,
        token_service: TokenService,
        password_service: PasswordService,
    ):
        self.dao = dao
        self.token_service = token_service
        self.password_service = password_service

    def _generate_refresh_token(self) -> str:
        return secrets.token_urlsafe(64)

    def _hash_refresh_token(self, token: str) -> str:
        return self.password_service.hash_refresh_token(token)

    async def _get_role_with_permissions(self, role_name: str) -> Role:
        stmt = (
            select(Role)
            .where(Role.name == role_name)
            .options(selectinload(Role.permissions))
        )
        result = await self.dao.session.execute(stmt)
        role = result.scalar_one_or_none()
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Role '{role_name}' is not configured",
            )
        return role

    async def _get_role_by_id_with_permissions(self, role_id: int) -> Role:
        stmt = (
            select(Role)
            .where(Role.id == role_id)
            .options(selectinload(Role.permissions))
        )
        result = await self.dao.session.execute(stmt)
        role = result.scalar_one_or_none()
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Role not found",
            )
        return role

    # ---------- register ----------

    async def register_customer(self, data: RegisterCustomerRequest) -> TokenResponse:
        existing = await self.dao.get_user_by_email(data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists",
            )

        password_hash = self.password_service.hash_password(data.password)
        role_name = "customer"

        role = await self._get_role_with_permissions(role_name)

        user = await self.dao.create_user(
            email=data.email,
            password_hash=password_hash,
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            role_id=role.id,
        )

        permissions = [perm.code for perm in role.permissions]

        access_token = self.token_service.create_access_token_generic(
            subject=str(user.id),
            role=role.name,
            principal_type="user",
            issuer="auth_service",
            audience="internal_api",
            token_type="access",
            custom_claims={
                "token_type": "user_access",
                "permissions": permissions,
            },
        )

        refresh_token, expires_at = self.token_service.create_refresh_token_generic(
            subject=str(user.id),
            issuer="auth_service",
            token_type="refresh",
        )

        refresh_hash = self.password_service.hash_refresh_token(refresh_token)
        await self.dao.create_session(
            user_id=user.id,
            refresh_token_hash=refresh_hash,
            expires_at=expires_at,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    # ---------- refresh ----------

    async def refresh(self, data: RefreshRequest) -> TokenResponse:
        refresh_token = data.refresh_token
        refresh_hash_candidate = self._hash_refresh_token(refresh_token)

        session_obj = await self.dao.get_active_session_by_refresh_hash(
            refresh_hash_candidate
        )
        if session_obj is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        if session_obj.expires_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired",
            )

        user = await self.dao.get_user_by_id(session_obj.user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        if user.role_id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User has no role assigned",
            )

        role = await self._get_role_by_id_with_permissions(user.role_id)
        permissions = [perm.code for perm in role.permissions]

        access_token = self.token_service.create_access_token_generic(
            subject=str(user.id),
            role=role.name,
            principal_type="user",
            issuer="auth_service",
            audience="internal_api",
            token_type="access",
            custom_claims={
                "token_type": "user_access",
                "permissions": permissions,
            },
        )

        new_refresh_token, new_expires_at = self.token_service.create_refresh_token_generic(
            subject=str(user.id),
            issuer="auth_service",
            token_type="refresh",
        )
        new_refresh_hash = self._hash_refresh_token(new_refresh_token)

        await self.dao.revoke_session(
            session_id=session_obj.id,
            revoked_at=datetime.now(timezone.utc),
        )
        await self.dao.create_session(
            user_id=user.id,
            refresh_token_hash=new_refresh_hash,
            expires_at=new_expires_at,
            device_id=data.device_id,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
        )

    async def logout(self, data: LogoutRequest) -> None:
        refresh_token = data.refresh_token
        refresh_hash_candidate = self._hash_refresh_token(refresh_token)
        session_obj = await self.dao.get_active_session_by_refresh_hash(
            refresh_hash_candidate
        )
        if session_obj is None:
            return

        await self.dao.revoke_session(
            session_id=session_obj.id,
            revoked_at=datetime.now(timezone.utc),
        )
    
    async def login(self, data: LoginRequest) -> TokenResponse:
        user = await self.dao.get_user_by_email(data.email)
        print(user)
        if user is None or not self.password_service.verify_password(
            data.password, user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is inactive",
            )

        if user.role_id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User has no role assigned",
            )

        # подгружаем роль и permissions из БД
        role = await self._get_role_by_id_with_permissions(user.role_id)
        permissions = [perm.code for perm in role.permissions]

        # генерируем access токен с RBAC
        access_token = self.token_service.create_access_token_generic(
            subject=str(user.id),
            role=role.name,
            principal_type="user",
            issuer="auth_service",
            audience="internal_api",
            token_type="access",
            custom_claims={
                "token_type": "user_access",
                "permissions": permissions,
            },
        )

        # создаём refresh токен и сессию (ротация по желанию)
        refresh_token, expires_at = self.token_service.create_refresh_token_generic(
            subject=str(user.id),
            issuer="auth_service",
            token_type="refresh",
        )
        refresh_hash = self._hash_refresh_token(refresh_token)

        await self.dao.create_session(
            user_id=user.id,
            refresh_token_hash=refresh_hash,
            expires_at=expires_at,
            device_id=data.device_id,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )