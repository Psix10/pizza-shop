from datetime import datetime, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.delivery import DeliveryJob
from schemas.delivery import DeliveryJobCreateInternal


class DeliveryDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_order_id(self, order_id: int) -> DeliveryJob | None:
        stmt = select(DeliveryJob).where(DeliveryJob.order_id == order_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_delivery_job(self, data: DeliveryJobCreateInternal) -> DeliveryJob:
        existing = await self.get_by_order_id(data.order_id)
        if existing:
            return existing

        job = DeliveryJob(
            order_id=data.order_id,
            store_id=data.store_id,
            address_id=data.address_id,
            status="assigned",
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def list_jobs(self) -> list[DeliveryJob]:
        stmt = select(DeliveryJob).order_by(DeliveryJob.assigned_at.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_job(self, job_id: int) -> DeliveryJob | None:
        stmt = select(DeliveryJob).where(DeliveryJob.id == job_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def accept_job(self, job_id: int, courier_id: int | None = None) -> DeliveryJob | None:
        job = await self.get_job(job_id)
        if not job:
            return None

        if job.status == "assigned" and courier_id is not None and job.courier_id is None:
            job.courier_id = courier_id
            await self.session.flush()
            return job

        return job

    async def pickup_job(self, job_id: int) -> DeliveryJob | None:
        job = await self.get_job(job_id)
        if not job:
            return None

        if job.status == "on_the_way":
            return job

        if job.status != "assigned":
            return job

        job.status = "on_the_way"
        if job.picked_up_at is None:
            job.picked_up_at = datetime.now(UTC)
        await self.session.flush()
        return job

    async def complete_job(self, job_id: int) -> DeliveryJob | None:
        job = await self.get_job(job_id)
        if not job:
            return None

        if job.status == "delivered":
            return job

        if job.status not in ("assigned", "on_the_way"):
            return job

        job.status = "delivered"
        if job.picked_up_at is None:
            job.picked_up_at = datetime.now(UTC)
        if job.delivered_at is None:
            job.delivered_at = datetime.now(UTC)
        await self.session.flush()
        return job