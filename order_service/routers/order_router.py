from decimal import Decimal
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, UTC

from db.db import get_session
from routers.deps import get_current_customer_id
from dao.idempotency_dao import IdempotencyDAO
from dao.cart_dao import CartDAO
from dao.order_dao import OrderDAO
from schemas.order import (
    CheckoutCreate,
    OrderRead,
    OrderShortRead,
    OrderStatusRead,
)
from schemas.cart import CartRead
from services.profile_client import get_address_for_user
from services.store_client import get_nearest_store, get_delivery_zones

router = APIRouter(prefix="/orders", tags=["orders"])


def get_cart_dao(session: AsyncSession = Depends(get_session)) -> CartDAO:
    return CartDAO(session)


def get_order_dao(session: AsyncSession = Depends(get_session)) -> OrderDAO:
    return OrderDAO(session)

def get_idempotency_dao(
    session: AsyncSession = Depends(get_session),
) -> IdempotencyDAO:
    return IdempotencyDAO(session)

@router.post("/checkout", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def checkout(
    data: CheckoutCreate,
    customer_id: int = Depends(get_current_customer_id),
    session: AsyncSession = Depends(get_session),
    cart_dao: CartDAO = Depends(get_cart_dao),
    order_dao: OrderDAO = Depends(get_order_dao),
    idempotency_dao: IdempotencyDAO = Depends(get_idempotency_dao),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key header is required",
        )

    existing_key = await idempotency_dao.get_key(
        customer_id=customer_id,
        key=idempotency_key,
        operation="checkout",
    )
    if existing_key and existing_key.order_id is not None:
        existing_order = await order_dao.get_order_by_id_for_customer(
            existing_key.order_id,
            customer_id,
        )
        if existing_order:
            return existing_order

    if not existing_key:
        existing_key = await idempotency_dao.create_key(
            customer_id=customer_id,
            key=idempotency_key,
            operation="checkout",
        )

    cart = await cart_dao.get_active_cart(customer_id)
    if cart is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty",
        )

    cart = await cart_dao.refresh_cart(cart)
    if not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty",
        )

    try:
        address = await get_address_for_user(data.address_id, customer_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Address not found",
        )

    lat = address.get("lat")
    lng = address.get("lng")
    if lat is None or lng is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Address does not have coordinates",
        )

    try:
        nearest_store = await get_nearest_store(lat=lat, lng=lng)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active stores for this address",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Store service unavailable",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Store service unavailable",
        )

    store_id = nearest_store.get("id")
    if store_id is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid response from store service",
        )

    promised_at = None
    try:
        zones = await get_delivery_zones(store_id)
        if zones:
            max_eta = max(zone["max_eta"] for zone in zones)
            promised_at = datetime.now(UTC) + timedelta(minutes=max_eta)
    except Exception:
        promised_at = None

    delivery_fee = 0.0

    order = await order_dao.create_order_from_cart(
        cart=cart,
        customer_id=customer_id,
        store_id=store_id,
        address_id=data.address_id,
        delivery_fee=delivery_fee,
        promised_at=promised_at,
    )

    await idempotency_dao.attach_order(existing_key, order.id)

    event = order_dao.build_order_created_event(order)
    await order_dao.save_outbox_event(
        event_name=event.event_name,
        payload=event.model_dump(mode="json"),
    )

    await session.commit()
    return order


@router.get(
    "/history",
    response_model=List[OrderShortRead],
)
async def get_order_history(
    customer_id: int = Depends(get_current_customer_id),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    dao: OrderDAO = Depends(get_order_dao),
):
    orders = await dao.list_orders_for_customer(
        customer_id=customer_id,
        limit=limit,
        offset=offset,
    )
    return orders


@router.get(
    "/{order_id}",
    response_model=OrderRead,
    summary="Get order with items",
)
async def get_order(
    order_id: int,
    customer_id: int = Depends(get_current_customer_id),
    dao: OrderDAO = Depends(get_order_dao),
):
    order = await dao.get_order_with_items(order_id, customer_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get(
    "/{order_id}/status",
    response_model=OrderStatusRead,
)
async def get_order_status(
    order_id: int,
    customer_id: int = Depends(get_current_customer_id),
    dao: OrderDAO = Depends(get_order_dao),
):
    status_rec = await dao.get_last_status_record(order_id, customer_id)
    if not status_rec:
        raise HTTPException(status_code=404, detail="Order not found")

    return OrderStatusRead(
        status=status_rec.status,
        changed_at=status_rec.changed_at,
    )

@router.post(
    "/{order_id}/repeat",
    response_model=CartRead,
    status_code=status.HTTP_201_CREATED,
)
async def repeat_order(
    order_id: int,
    customer_id: int = Depends(get_current_customer_id),
    session: AsyncSession = Depends(get_session),
    cart_dao: CartDAO = Depends(get_cart_dao),
    order_dao: OrderDAO = Depends(get_order_dao),
):
    order = await order_dao.get_order_for_customer(order_id, customer_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot repeat cancelled order",
        )

    cart = await cart_dao.create_cart(
        customer_id=customer_id,
        store_id=order.store_id,
    )

    for item in order.items:
        await cart_dao.add_item(
            cart=cart,
            product_variant_id=item.product_variant_id,
            qty=item.qty,
            unit_price=Decimal(str(item.unit_price)),
            snapshot_json=item.modifiers_json,
        )

    cart = await cart_dao.refresh_cart(cart)
    await session.commit()
    return cart


@router.post(
    "/{order_id}/cancel",
    response_model=OrderRead,
)
async def cancel_order(
    order_id: int,
    customer_id: int = Depends(get_current_customer_id),
    session: AsyncSession = Depends(get_session),
    order_dao: OrderDAO = Depends(get_order_dao),
):
    order = await order_dao.cancel_order(order_id, customer_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    await session.commit()
    return order