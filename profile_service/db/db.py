# db/db.py – свой для profile_service
import os

from typing import AsyncGenerator
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres_profile_db")

DATABASE_URL = (
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:5432/{POSTGRES_DB}"
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
    from models.profile import Profile, Address
    async with async_session() as session:
        # есть ли хоть один профиль
        result = await session.execute(select(Profile).limit(1))
        profile = result.scalar_one_or_none()
        if profile:
            return

        demo_profile = Profile(
            user_id=1,
            avatar_url="test_url",
            birth_date=date(2020, 1, 1),
            messenger="telega"
            
        )

        demo_address = Address(
            user_id=1,
            label="Дом",
            city="Москва",
            street="Тверская",
            house="1",
            apartment="1",
            lat=55.757,
            lng=37.615,
            is_default=True,
        )

        session.add_all([demo_profile, demo_address])
        await session.commit()