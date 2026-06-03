# dao/user_dao.py
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.auth import UserUpdateRequest
from services.password_service import hash_password, verify_password
from models.user import User
from models.role import Role
from models.user_session import UserSession


class UserDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(
        self,
        *,
        user_id: int,
        refresh_token_hash: str,
        expires_at: datetime,
        device_id: str | None = None,
    ) -> UserSession:
        session_obj = UserSession(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            device_id=device_id,
        )
        self.session.add(session_obj)
        await self.session.flush()
        return session_obj

    async def get_active_session_by_refresh_hash(
        self,
        refresh_token_hash: str,
    ) -> UserSession | None:
        stmt = select(UserSession).where(
            UserSession.refresh_token_hash == refresh_token_hash,
            UserSession.revoked_at.is_(None),
        )
        return await self.session.scalar(stmt)

    async def revoke_session(self, session_id: int, revoked_at: datetime) -> None:
        session_obj = await self.session.get(UserSession, session_id)
        if session_obj is None:
            return

        session_obj.revoked_at = revoked_at
        await self.session.flush()
    
    async def get_user_by_email(self, email: str) -> User | None:
        stmt = (
            select(User)
            .where(User.email == email)
            .options(
                selectinload(User.role).selectinload(Role.permissions)
            )
        )
        return await self.session.scalar(stmt)

    async def get_user_by_id(self, user_id: int) -> User | None:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.role).selectinload(Role.permissions),
                selectinload(User.sessions),
            )
        )
        return await self.session.scalar(stmt)

    async def create_user(
        self,
        *,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        phone: str | None,
        role_id: int,
        is_active: bool = True,
        is_verified: bool = False,
    ) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role_id=role_id,
            is_active=is_active,
            is_verified=is_verified,
        )
        self.session.add(user)
        await self.session.flush()
        return user
    
    async def update_user_fields(self, user_id: int, fields: UserUpdateRequest) -> User:
        data = fields.model_dump(exclude_unset=True)
        user = await self.session.get(User, user_id)
        if user is None:
            # по идее не должно случаться, current_user уже проверен
            raise ValueError("User not found")

        for key, value in data.items():
            setattr(user, key, value)

        await self.session.flush()
        await self.session.refresh(user)
        return user
    
    async def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        user = await self.session.get(User, user_id)
        if user is None:
            return False

        # проверить текущий пароль
        if not verify_password(current_password, user.password_hash):
            return False

        # захешить новый
        new_hash = hash_password(new_password)
        user.password_hash = new_hash

        await self.session.flush()
        return True
    
    async def change_email(self, user_id: int, new_email: str) -> User:
        # проверить, что email свободен
        stmt = select(User).where(User.email == new_email)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing and existing.id != user_id:
            raise EmailAlreadyExistsError

        user = await self.session.get(User, user_id)
        if user is None:
            raise ValueError("User not found")

        user.email = new_email
        # по желанию: user.is_verified = False

        await self.session.flush()
        await self.session.refresh(user)
        return user