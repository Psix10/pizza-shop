from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from db.db import get_session
from dao.delivery_dao import DeliveryDAO
from services.order_client import update_order_status
from schemas.delivery import DeliveryJobCreateInternal, DeliveryJobRead


router = APIRouter(prefix="/delivery/jobs", tags=["delivery"])


def get_delivery_dao(session: AsyncSession = Depends(get_session)) -> DeliveryDAO:
    return DeliveryDAO(session)


@router.post("/internal", response_model=DeliveryJobRead, status_code=status.HTTP_201_CREATED)
async def create_delivery_job_internal(
    data: DeliveryJobCreateInternal,
    session: AsyncSession = Depends(get_session),
    dao: DeliveryDAO = Depends(get_delivery_dao),
):
    job = await dao.create_delivery_job(data)
    await session.commit()
    return job


@router.get("", response_model=list[DeliveryJobRead])
async def list_delivery_jobs(
    dao: DeliveryDAO = Depends(get_delivery_dao),
):
    return await dao.list_jobs()


@router.get("/{job_id}", response_model=DeliveryJobRead)
async def get_delivery_job(
    job_id: int,
    dao: DeliveryDAO = Depends(get_delivery_dao),
):
    job = await dao.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Delivery job not found")
    return job


@router.post("/{job_id}/accept", response_model=DeliveryJobRead)
async def accept_delivery_job(
    job_id: int,
    courier_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    dao: DeliveryDAO = Depends(get_delivery_dao),
):
    job = await dao.accept_job(job_id, courier_id=courier_id)
    if not job:
        raise HTTPException(status_code=404, detail="Delivery job not found")

    await session.commit()
    return job


@router.post("/{job_id}/pickup", response_model=DeliveryJobRead)
async def pickup_delivery_job(
    job_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    dao: DeliveryDAO = Depends(get_delivery_dao),
):
    user_id_header = request.headers.get("x-user-id")
    courier_id = int(user_id_header) if user_id_header else None
    correlation_id = getattr(request.state, "correlation_id", None)

    job = await dao.pickup_job(job_id, courier_id=courier_id, correlation_id=correlation_id)
    if not job:
        raise HTTPException(status_code=404, detail="Delivery job not found")

    try:
        await update_order_status(
            order_id=job.order_id,
            status_value="on_the_way",
        )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Order service unavailable",
        )

    await session.commit()
    return job


@router.post("/{job_id}/complete", response_model=DeliveryJobRead)
async def complete_delivery_job(
    job_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    dao: DeliveryDAO = Depends(get_delivery_dao),
):
    user_id_header = request.headers.get("x-user-id")
    courier_id = int(user_id_header) if user_id_header else None

    job = await dao.complete_job(job_id, courier_id=courier_id)
    if not job:
        raise HTTPException(status_code=404, detail="Delivery job not found")

    try:
        await update_order_status(
            order_id=job.order_id,
            status_value="delivered",
        )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Order service unavailable",
        )

    await session.commit()
    return job