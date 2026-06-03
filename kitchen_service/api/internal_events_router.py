from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.db import get_session
from dao.kitchen_dao import KitchenDAO
from schemas.events import OrderCreatedEvent


router = APIRouter(prefix="/internal/events", tags=["internal-events"])


def get_kitchen_dao(session: AsyncSession = Depends(get_session)) -> KitchenDAO:
    return KitchenDAO(session)


@router.post("/order-created", status_code=status.HTTP_202_ACCEPTED)
async def handle_order_created(
    event: OrderCreatedEvent,
    session: AsyncSession = Depends(get_session),
    dao: KitchenDAO = Depends(get_kitchen_dao),
):
    job = await dao.create_job_from_order_created(event)
    await session.commit()

    return {
        "kitchen_job_id": job.id,
        "order_id": job.order_id,
        "status": job.status,
    }