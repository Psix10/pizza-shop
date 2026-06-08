# services/outbox_dispatcher.py
from __future__ import annotations

import asyncio
import logging

from db.db import async_session
from dao.outbox_dao import OutboxDAO
from services.broker_event_relay import BrokerEventRelay

logger = logging.getLogger(__name__)


class OutboxDispatcher:
    def __init__(self, poll_interval: float = 2.0, batch_size: int = 50):
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self.relay = BrokerEventRelay(source_service="order_service")
        self._running = True

    def stop(self) -> None:
        self._running = False

    async def flush_once(self) -> dict:
        async with async_session() as session:
            outbox_dao = OutboxDAO(session)
            events = await outbox_dao.lock_pending_events(limit=self.batch_size)

            published = 0
            failed = 0

            for event in events:
                try:
                    await self.relay.publish(event)
                    await outbox_dao.mark_as_published(event)
                    published += 1
                except Exception as e:
                    await outbox_dao.mark_as_failed(event, str(e))
                    failed += 1
                    logger.exception("Outbox publish failed for event_id=%s", event.id)

            await session.commit()

            return {
                "processed": len(events),
                "published": published,
                "failed": failed,
            }

    async def run_forever(self) -> None:
        while self._running:
            try:
                result = await self.flush_once()
                if result["processed"] == 0:
                    await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Outbox dispatcher loop failed")
                await asyncio.sleep(self.poll_interval)