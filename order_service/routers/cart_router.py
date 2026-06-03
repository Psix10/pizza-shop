from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.db import get_session
from dao.cart_dao import CartDAO
from schemas.cart import CartRead, CartItemCreate, CartItemUpdate
from .deps import get_current_customer_id
from services.catalog_client import get_product_variant


router = APIRouter(prefix="/cart", tags=["cart"])


def get_cart_dao(session: AsyncSession = Depends(get_session)) -> CartDAO:
    return CartDAO(session)


@router.get("", response_model=CartRead)
async def get_cart(
    customer_id: int = Depends(get_current_customer_id),
    dao: CartDAO = Depends(get_cart_dao),
):
    cart = await dao.get_active_cart(customer_id)
    if cart is None:
        cart = await dao.create_cart(customer_id=customer_id)
    return cart


@router.post("/items", response_model=CartRead, status_code=status.HTTP_201_CREATED)
async def add_cart_item(
    data: CartItemCreate,
    customer_id: int = Depends(get_current_customer_id),
    session: AsyncSession = Depends(get_session),
    dao: CartDAO = Depends(get_cart_dao),
):
    cart = await dao.get_active_cart(customer_id)
    if cart is None:
        cart = await dao.create_cart(customer_id=customer_id)

    try:
        variant = await get_product_variant(data.product_variant_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product variant not found",
        )

    unit_price = Decimal(str(variant["base_price"]))
    snapshot_json = data.snapshot_json if hasattr(data, "snapshot_json") else None

    cart = await dao.add_item(
        cart=cart,
        product_variant_id=data.product_variant_id,
        qty=data.qty,
        unit_price=unit_price,
        snapshot_json=snapshot_json,
    )

    await session.commit()
    cart = await dao.get_active_cart(customer_id)
    return cart


@router.patch("/items/{item_id}", response_model=CartRead)
async def update_cart_item(
    item_id: int,
    data: CartItemUpdate,
    customer_id: int = Depends(get_current_customer_id),
    session: AsyncSession = Depends(get_session),
    dao: CartDAO = Depends(get_cart_dao),
):
    cart = await dao.get_active_cart(customer_id)
    if cart is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found",
        )

    item = await dao.update_item_qty(cart, item_id, data.qty)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found",
        )

    await session.commit()
    cart = await dao.refresh_cart(cart)
    return cart


@router.delete("/items/{item_id}", response_model=CartRead)
async def delete_cart_item(
    item_id: int,
    customer_id: int = Depends(get_current_customer_id),
    session: AsyncSession = Depends(get_session),
    dao: CartDAO = Depends(get_cart_dao),
):
    cart = await dao.get_active_cart(customer_id)
    if cart is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found",
        )

    deleted = await dao.delete_item(cart, item_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found",
        )

    await session.commit()
    cart = await dao.refresh_cart(cart)
    return cart