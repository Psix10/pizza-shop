# delivery_service/services/outbox_publisher.py
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, UTC

import aio_pika
from aio_pika import ExchangeType
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.db import async_session
from models.outbox import OutboxEvent

logger = logging.getLogger(__name__)

RABBITMQ_URL = "amqp://guest:guest@rabbitmq:5672/"
EVENT_EXCHANGE = "domain_events"


async def publish_pending_events_once() -> None:
    async with async_session() as session:  # свой фабричный метод
        await _publish_batch(session)


async def _publish_batch(session: AsyncSession, limit: int = 50) -> None:
    # забираем pending события
    stmt = (
        select(OutboxEvent)
        .where(OutboxEvent.status == "pending")
        .order_by(OutboxEvent.created_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    result = await session.execute(stmt)
    events: list[OutboxEvent] = list(result.scalars().all())
    if not events:
        return

    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    try:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(
            EVENT_EXCHANGE,
            ExchangeType.TOPIC,
            durable=True,
        )

        for ev in events:
            try:
                envelope = json.loads(ev.payload_json)
                # дополняем event_name, если нужно
                if "event_name" not in envelope:
                    envelope["event_name"] = ev.event_name

                body = json.dumps(envelope, default=str).encode("utf-8")
                routing_key = ev.event_name  # например: delivery.picked_up

                await exchange.publish(
                    aio_pika.Message(
                        body=body,
                        content_type="application/json",
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    ),
                    routing_key=routing_key,
                )

                ev.status = "sent"
                ev.sent_at = datetime.now(UTC)
                ev.last_error = None
            except Exception as exc:  # пер‑event обработка
                logger.exception("Failed to publish event id=%s", ev.id)
                ev.status = "failed"
                ev.last_error = str(exc)

        await session.commit()
    finally:
        await connection.close()


async def outbox_worker(loop_interval: float = 1.0) -> None:
    """Фоновый воркер: раз в loop_interval секунд шлёт pending события."""
    while True:
        try:
            await publish_pending_events_once()
        except Exception:
            logger.exception("Outbox worker iteration failed")
        await asyncio.sleep(loop_interval)