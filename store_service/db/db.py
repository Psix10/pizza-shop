# db/db.py – свой для profile_service
import os
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase



POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres_store_db")

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
    from models.store import Store, StoreCapacity, DeliveryZone
    async with async_session() as session:
        result = await session.execute(select(Store).limit(1))
        store = result.scalar_one_or_none()
        if store:
            return

        moscow_store = Store(
            name="Пиццерия №1",
            phone="+7-900-000-00-01",
            address="Москва, Тверская, 1",
            lat=55.757,
            lng=37.615,
            timezone="Europe/Moscow",
            is_active=True,
        )

        capacity = StoreCapacity(
            store=moscow_store,
            max_parallel_orders=10,
            courier_pool_size=5,
        )

        zone = DeliveryZone(
            store=moscow_store,
            zone_name="Центр",
            polygon_geojson='{"type":"Polygon","coordinates":[[[37.60,55.75],[37.62,55.75],[37.62,55.76],[37.60,55.76],[37.60,55.75]]]}',
            min_eta=30,
            max_eta=45,
        )

        session.add(moscow_store)
        await session.commit()