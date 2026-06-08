from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import select

import os


from services.password_service import hash_password


POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")

DATABASE_URL = (
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@postgres_auth_db:5432/{POSTGRES_DB}"
)

class Base(DeclarativeBase):
    pass

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def init_seed():
    from models.user import User, Role
    async with async_session() as session:
        # Проверим, есть ли уже пользователи
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if user:
            return

        # Создаём базовую роль "user", если её нет
        result = await session.execute(select(Role).where(Role.name == "admin"))
        role = result.scalar_one_or_none()
        if role is None:
            role = Role(name="admin", description="Default admin role")
            session.add(role)
            await session.flush()
            await session.refresh(role)

        demo_user = User(
            email="demo@pizza.com",
            password_hash=hash_password("password"),
            first_name="Demo",
            last_name="User",
            phone="+70000000001",
            role_id=role.id,
            is_active=True,
            is_verified=True,
        )

        session.add(demo_user)
        await session.commit()