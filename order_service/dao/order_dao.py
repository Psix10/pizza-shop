from __future__ import annotations

import json
from decimal import Decimal
from typing import Optional
from datetime import datetime, UTC

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.order import Cart, Order, OrderItem, OrderStatusHistory
from models.outbox import OutboxEvent
from schemas.events import OrderCreatedEvent, OrderCreatedItemEvent

class OrderDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_order_with_items(self, order_id: int, customer_id: int) -> Optional[Order]:
        stmt = (
            select(Order)
            .where(Order.id == order_id, Order.customer_id == customer_id)
            .options(selectinload(Order.items))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_order_from_cart(
        self,
        cart: Cart,
        customer_id: int,
        store_id: int,
        address_id: int,
        delivery_fee: float = 0.0,
        promised_at: datetime | None = None,
    ) -> Order:
        if not cart.items:
            raise ValueError("Cannot create order from empty cart")

        subtotal = Decimal("0.00")
        for cart_item in cart.items:
            subtotal += cart_item.unit_price * cart_item.qty

        delivery_fee_dec = Decimal(str(delivery_fee))
        total = subtotal + delivery_fee_dec

        order = Order(
            order_no="",
            customer_id=customer_id,
            store_id=store_id,
            address_id=address_id,
            status="created",
            subtotal=subtotal,
            delivery_fee=delivery_fee_dec,
            total_amount=total,
            promised_at=promised_at,
        )
        self.session.add(order)
        await self.session.flush()

        order.order_no = f"ORD-{order.id}"

        status_rec = OrderStatusHistory(
            order_id=order.id,
            status="created",
            changed_by=customer_id,
        )
        self.session.add(status_rec)

        for cart_item in cart.items:
            product_name = "Pizza"
            variant_name = "30 см"

            if cart_item.snapshot_json:
                try:
                    snap = json.loads(cart_item.snapshot_json)
                    product_name = snap.get("product_name", product_name)
                    variant_name = snap.get("variant_name", variant_name)
                except json.JSONDecodeError:
                    pass

            order_item = OrderItem(
                order_id=order.id,
                product_variant_id=cart_item.product_variant_id,
                product_name=product_name,
                variant_name=variant_name,
                qty=cart_item.qty,
                unit_price=cart_item.unit_price,
                modifiers_json=cart_item.snapshot_json,
            )
            self.session.add(order_item)

        cart.status = "checked_out"
        await self.session.flush()

        stmt = (
            select(Order)
            .where(Order.id == order.id)
            .options(selectinload(Order.items))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def list_orders_for_customer(
        self,
        customer_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Order]:
        stmt = (
            select(Order)
            .where(Order.customer_id == customer_id)
            .order_by(Order.placed_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_order_status(
        self,
        order_id: int,
        customer_id: int,
    ) -> Optional[Order]:
        stmt = select(Order).where(
            Order.id == order_id,
            Order.customer_id == customer_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_order_for_customer(
        self,
        order_id: int,
        customer_id: int,
    ) -> Optional[Order]:
        stmt = (
            select(Order)
            .where(Order.id == order_id, Order.customer_id == customer_id)
            .options(selectinload(Order.items))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def cancel_order(
        self,
        order_id: int,
        customer_id: int,
    ) -> Optional[Order]:
        stmt = (
            select(Order)
            .where(Order.id == order_id, Order.customer_id == customer_id)
            .options(selectinload(Order.items))
        )
        result = await self.session.execute(stmt)
        order = result.scalar_one_or_none()
        if not order:
            return None

        if order.status in ("cancelled", "completed"):
            return order

        order.status = "cancelled"

        status_rec = OrderStatusHistory(
            order_id=order.id,
            status="cancelled",
            changed_by=customer_id,
        )
        self.session.add(status_rec)

        await self.session.flush()
        return order

    async def get_last_status_record(
        self,
        order_id: int,
        customer_id: int,
    ) -> Optional[OrderStatusHistory]:
        stmt_order = select(Order).where(
            Order.id == order_id,
            Order.customer_id == customer_id,
        )
        result_order = await self.session.execute(stmt_order)
        order = result_order.scalar_one_or_none()
        if not order:
            return None

        stmt_status = (
            select(OrderStatusHistory)
            .where(OrderStatusHistory.order_id == order_id)
            .order_by(desc(OrderStatusHistory.changed_at))
            .limit(1)
        )
        result_status = await self.session.execute(stmt_status)
        return result_status.scalar_one_or_none()
    
    async def save_outbox_event(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_name: str,
        payload: dict,
    ) -> OutboxEvent:
        event = OutboxEvent(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_name=event_name,
            payload_json=json.dumps(payload, default=str),
            status="pending",
            retry_count=0,
            created_at=datetime.now(UTC),
        )
        self.session.add(event)
        await self.session.flush()
        return event
    
    def build_order_created_event(self, order: Order) -> OrderCreatedEvent:
        return OrderCreatedEvent(
            order_id=order.id,
            order_no=order.order_no,
            customer_id=order.customer_id,
            store_id=order.store_id,
            address_id=order.address_id,
            status=order.status,
            subtotal=order.subtotal,
            delivery_fee=order.delivery_fee,
            total_amount=order.total_amount,
            placed_at=order.placed_at,
            promised_at=order.promised_at,
            items=[
                OrderCreatedItemEvent(
                    product_variant_id=item.product_variant_id,
                    product_name=item.product_name,
                    variant_name=item.variant_name,
                    qty=item.qty,
                    unit_price=item.unit_price,
                )
                for item in order.items
            ],
        )
    
    async def update_order_status_internal(
        self,
        order_id: int,
        status_value: str,
        changed_by: int | None = None,
        changed_at: datetime | None = None,
    ) -> Order | None:
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items))
        )
        result = await self.session.execute(stmt)
        order = result.scalar_one_or_none()
        if not order:
            return None

        if order.status == status_value:
            return order

        if changed_at is None:
            changed_at = datetime.now(UTC)

        if changed_at.tzinfo is not None:
            changed_at = changed_at.astimezone(UTC).replace(tzinfo=None)

        order.status = status_value

        status_rec = OrderStatusHistory(
            order_id=order.id,
            status=status_value,
            changed_by=changed_by,
            changed_at=changed_at,
        )
        self.session.add(status_rec)

        await self.session.flush()
        return order
