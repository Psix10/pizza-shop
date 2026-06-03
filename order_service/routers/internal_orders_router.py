from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.db import get_session
from dao.order_dao import OrderDAO
from schemas.internal_order import OrderStatusUpdateInternal


router = APIRouter(prefix="/internal/orders", tags=["internal-orders"])


def get_order_dao(session: AsyncSession = Depends(get_session)) -> OrderDAO:
    return OrderDAO(session)


@router.post("/{order_id}/status", status_code=status.HTTP_200_OK)
async def update_order_status_internal(
    order_id: int,
    data: OrderStatusUpdateInternal,
    session: AsyncSession = Depends(get_session),
    dao: OrderDAO = Depends(get_order_dao),
):
    order = await dao.update_order_status_internal(
        order_id=order_id,
        status_value=data.status,
        changed_by=data.changed_by,
        changed_at=data.changed_at,
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    await session.commit()
    return {
        "order_id": order.id,
        "status": order.status,
    }