# db/db.py – свой для profile_service
import os
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres_catalog_db")

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
    from models.catalog import Category, Product, ProductVariant
    async with async_session() as session:
        # есть ли хоть одна категория
        result = await session.execute(select(Category).limit(1))
        category = result.scalar_one_or_none()
        if category:
            return

        cat_pizza = Category(
            name="Пицца",
            sort_order=1,
            is_active=True,
        )

        product = Product(
            category=cat_pizza,
            name="Пепперони",
            description="Классическая пицца с пепперони",
            image_url=None,
            is_active=True,
        )

        variant_30 = ProductVariant(
            product=product,
            size="30 см",
            sku="PEP-30",
            base_price=450.0,
            weight_g=500,
            is_active=True,
        )

        variant_40 = ProductVariant(
            product=product,
            size="40 см",
            sku="PEP-40",
            base_price=650.0,
            weight_g=750,
            is_active=True,
        )

        session.add(cat_pizza)
        await session.commit()