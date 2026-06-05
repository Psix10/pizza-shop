import httpx

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.db import get_session
from dao.kitchen_dao import KitchenDAO
from schemas.kitchen import KitchenJobRead
from services.order_client import update_order_status
from services.delivery_client import create_delivery_job

router = APIRouter(prefix="/kitchen/jobs", tags=["kitchen"])


def get_kitchen_dao(session: AsyncSession = Depends(get_session)) -> KitchenDAO:
    return KitchenDAO(session)


@router.get("", response_model=list[KitchenJobRead])
async def list_kitchen_jobs(
    dao: KitchenDAO = Depends(get_kitchen_dao),
):
    return await dao.list_jobs()


@router.get("/{job_id}", response_model=KitchenJobRead)
async def get_kitchen_job(
    job_id: int,
    dao: KitchenDAO = Depends(get_kitchen_dao),
):
    job = await dao.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Kitchen job not found")
    return job


@router.post("/{job_id}/accept", response_model=KitchenJobRead)
async def accept_kitchen_job(
    job_id: int,
    session: AsyncSession = Depends(get_session),
    dao: KitchenDAO = Depends(get_kitchen_dao),
):
    job = await dao.accept_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Kitchen job not found")

    await session.commit()
    return job


@router.post("/{job_id}/start", response_model=KitchenJobRead)
async def start_kitchen_job(
    job_id: int,
    session: AsyncSession = Depends(get_session),
    dao: KitchenDAO = Depends(get_kitchen_dao),
):
    job = await dao.start_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Kitchen job not found")

    await session.commit()
    return job


@router.post("/{job_id}/complete", response_model=KitchenJobRead)
async def complete_kitchen_job(
    job_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    dao: KitchenDAO = Depends(get_kitchen_dao),
):
    correlation_id = getattr(request.state, "correlation_id", None)

    job = await dao.complete_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Kitchen job not found")

    try:
        await update_order_status(
            order_id=job.order_id,
            status="delivery_pending",
            correlation_id=correlation_id,
        )

        await create_delivery_job(
            order_id=job.order_id,
            store_id=job.store_id,
            address_id=job.address_id,
        )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=502,
            detail="Dependent service unavailable",
        )

    await session.commit()
    return job