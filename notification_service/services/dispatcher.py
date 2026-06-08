# notification_service/services/dispatcher.py
from __future__ import annotations

import asyncio
import logging

from db.db import async_session
from dao.notification_dao import NotificationDAO

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    def __init__(self, poll_interval: float = 2.0, batch_size: int = 50):
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self._running = True

    def stop(self) -> None:
        self._running = False

    async def flush_once(self) -> dict:
        async with async_session() as session:
            dao = NotificationDAO(session)
            items = await dao.lock_pending_notifications(limit=self.batch_size)

            sent = 0
            failed = 0

            for item in items:
                try:
                    # тут вместо print/логов можно дергать реальных провайдеров push/email/SMS
                    logger.info(
                        "Sending notification id=%s user=%s channel=%s event=%s payload=%s",
                        item.id,
                        item.recipient_user_id,
                        item.channel,
                        item.event_type,
                        item.payload_json,
                    )
                    await dao.mark_as_sent(item)
                    sent += 1
                except Exception as exc:
                    await dao.mark_as_failed(item, str(exc))
                    failed += 1
                    logger.exception("Failed to send notification id=%s", item.id)

            await session.commit()

            return {
                "processed": len(items),
                "sent": sent,
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
                logger.exception("NotificationDispatcher loop failed")
                await asyncio.sleep(self.poll_interval)