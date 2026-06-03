from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.order import Cart, CartItem


class CartDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_cart(self, customer_id: int) -> Optional[Cart]:
        stmt = (
            select(Cart)
            .where(Cart.customer_id == customer_id, Cart.status == "active")
            .options(selectinload(Cart.items))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_cart(self, customer_id: int, store_id: int | None = None) -> Cart:
        cart = Cart(
            customer_id=customer_id,
            store_id=store_id,
            status="active",
            total_amount=0,
        )
        self.session.add(cart)
        await self.session.flush()
        # сразу подгружаем items (их ноль, но структура есть)
        await self.session.refresh(cart, ["items"])
        return cart

    async def refresh_cart(self, cart: Cart) -> Cart:
        stmt = (
            select(Cart)
            .where(Cart.id == cart.id)
            .options(selectinload(Cart.items))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def recalculate_total(self, cart: Cart) -> None:
        cart = await self.refresh_cart(cart)
        total = Decimal("0.00")
        for item in cart.items:
            total += item.unit_price * item.qty
        cart.total_amount = total
        await self.session.flush()

    async def add_item(
        self,
        cart: Cart,
        product_variant_id: int,
        qty: int,
        unit_price: Decimal,
        snapshot_json: str | None = None,
    ) -> CartItem:
        item = CartItem(
            cart_id=cart.id,
            product_variant_id=product_variant_id,
            qty=qty,
            unit_price=unit_price,
            snapshot_json=snapshot_json,
        )
        self.session.add(item)
        await self.session.flush()

        await self.recalculate_total(cart)
        await self.session.refresh(item)
        return item

    async def update_item_qty(self, cart: Cart, item_id: int, qty: int) -> Optional[CartItem]:
        cart = await self.refresh_cart(cart)
        for item in cart.items:
            if item.id == item_id:
                item.qty = qty
                await self.session.flush()
                await self.recalculate_total(cart)
                await self.session.refresh(item)
                return item
        return None


    async def delete_item(self, cart: Cart, item_id: int) -> bool:
        cart = await self.refresh_cart(cart)
        for item in cart.items:
            if item.id == item_id:
                await self.session.delete(item)
                await self.session.flush()
                await self.recalculate_total(cart)
                self.session.expire(cart, ["items"])
                return True
        return False