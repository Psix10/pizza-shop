from __future__ import annotations

from datetime import datetime, UTC
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.kitchen import KitchenJob
from models.outbox import OutboxEvent
from schemas.events import OrderCreatedEvent
from common.correlation import get_correlation_id


class KitchenDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_order_id(self, order_id: int) -> KitchenJob | None:
        stmt = select(KitchenJob).where(KitchenJob.order_id == order_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_kitchen_job_from_order(
        self,
        order_id: int,
        store_id: int,
        address_id: int,
        items: list[dict[str, Any]],
        correlation_id: str | None,
        customer_id: int | None = None,
    ) -> KitchenJob:
        existing = await self.get_by_order_id(order_id)
        if existing:
            return existing

        job = KitchenJob(
            order_id=order_id,
            store_id=store_id,
            address_id=address_id,
            customer_id=customer_id,  # вот это ключевое
            priority_score=0,
            status="queued",
            # если ты ещё где-то items сохраняешь – оставь как есть
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def create_job_from_order_created(
        self,
        event: OrderCreatedEvent,
    ) -> KitchenJob:
        existing = await self.get_by_order_id(event.order_id)
        if existing:
            return existing

        job = KitchenJob(
            order_id=event.order_id,
            store_id=event.store_id,
            address_id=event.address_id,
            customer_id=event.customer_id,
            priority_score=0,
            status="queued",
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def list_jobs(self) -> list[KitchenJob]:
        stmt = select(KitchenJob).order_by(KitchenJob.queued_at.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_job(self, job_id: int) -> KitchenJob | None:
        stmt = select(KitchenJob).where(KitchenJob.id == job_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def accept_job(self, job_id: int) -> KitchenJob | None:
        job = await self.get_job(job_id)
        if not job:
            return None

        if job.status in ("accepted", "preparing", "ready_for_delivery"):
            return job

        if job.status != "queued":
            return job

        job.status = "accepted"
        await self.session.flush()
        return job

    async def start_job(self, job_id: int) -> KitchenJob | None:
        job = await self.get_job(job_id)
        if not job:
            return None

        if job.status == "preparing":
            return job

        if job.status not in ("queued", "accepted"):
            return job

        job.status = "preparing"
        if job.started_at is None:
            job.started_at = datetime.now(UTC)
        await self.session.flush()
        return job

    async def complete_job(
        self,
        job_id: int,
        correlation_id: str | None = None,
    ) -> KitchenJob | None:
        job = await self.get_job(job_id)
        if not job:
            return None

        if job.status == "ready_for_delivery":
            return job

        if job.status not in ("accepted", "preparing"):
            return job

        job.status = "ready_for_delivery"
        if job.started_at is None:
            job.started_at = datetime.now(UTC)
        if job.finished_at is None:
            job.finished_at = datetime.now(UTC)

        # Outbox: публикуем kitchen.order.ready
        corr_id = correlation_id

        payload = {
            "payload": {
                "order_id": job.order_id,
                "store_id": job.store_id,
                "address_id": job.address_id,
                "priority_score": job.priority_score,
                "customer_id": job.customer_id,
            },
            "metadata": {
                "correlation_id": corr_id,
                "source_service": "kitchen_service",
                "schema_version": "1",
            },
        }

        event = OutboxEvent(
            aggregate_type="order",
            aggregate_id=str(job.order_id),
            event_name="kitchen.order.ready",
            payload_json=json.dumps(payload, default=str),
            status="pending",
            created_at=datetime.now(UTC),
        )

        self.session.add(event)
        await self.session.flush()
        return job

    async def cancel_kitchen_job(
        self,
        order_id: int,
        correlation_id: str | None = None,
    ) -> KitchenJob | None:
        job = await self.get_by_order_id(order_id)
        if not job:
            return None

        if job.status == "cancelled":
            return job

        job.status = "cancelled"
        await self.session.flush()
        return job