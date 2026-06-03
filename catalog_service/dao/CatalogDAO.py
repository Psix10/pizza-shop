from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.catalog import Category, Product, ProductVariant


class CatalogDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_categories(self) -> list[Category]:
        stmt = (
            select(Category)
            .where(Category.is_active.is_(True))
            .order_by(Category.sort_order)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_products(self) -> list[Product]:
        stmt = (
            select(Product)
            .where(Product.is_active.is_(True))
            .options(selectinload(Product.variants))  # подгружаем варианты
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_product(self, product_id: int) -> Product | None:
        stmt = (
            select(Product)
            .where(Product.id == product_id, Product.is_active.is_(True))
            .options(selectinload(Product.variants))  # и здесь тоже
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_product_variant(self, variant_id: int) -> ProductVariant | None:
        stmt = (
            select(ProductVariant)
            .where(ProductVariant.id == variant_id, ProductVariant.is_active.is_(True))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()