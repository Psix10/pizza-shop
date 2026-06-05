# dao/outbox_dao.py
from __future__ import annotations

import json
from datetime import datetime, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.outbox import OutboxEvent


class OutboxDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def lock_pending_events(self, limit: int = 50) -> list[OutboxEvent]:
        stmt = (
            select(OutboxEvent)
            .where(OutboxEvent.status == "pending")
            .order_by(OutboxEvent.id.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_as_published(self, event: OutboxEvent) -> None:
        event.status = "published"
        event.published_at = datetime.now(UTC)
        await self.session.flush()

    async def mark_as_failed(self, event: OutboxEvent, error: str | None = None) -> None:
        event.status = "failed"
        if hasattr(event, "error_message"):
            event.error_message = error
        await self.session.flush()

    async def save_outbox_event(self, event_name: str, payload: dict) -> OutboxEvent:
        event = OutboxEvent(
            event_name=event_name,
            payload_json=json.dumps(payload, default=str),
            status="pending",
        )
        self.session.add(event)
        await self.session.flush()
        return event