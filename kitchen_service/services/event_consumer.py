from __future__ import annotations

import json
import logging
from typing import Any

import aio_pika
from aio_pika import ExchangeType, IncomingMessage

from db.db import async_session
from dao.kitchen_dao import KitchenDAO
from schemas.events import OrderCreatedEvent


logger = logging.getLogger(__name__)


class KitchenEventConsumer:
    QUEUE_NAME = "kitchen_events"

    def __init__(self, rabbit_url: str, exchange_name: str = "domain_events"):
        self.rabbit_url = rabbit_url
        self.exchange_name = exchange_name
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.abc.AbstractRobustChannel | None = None
        self._queue: aio_pika.abc.AbstractQueue | None = None
        self._consume_tag: str | None = None
        self._started = False

    async def start(self) -> None:
        if self._started:
            return

        self._connection = await aio_pika.connect_robust(self.rabbit_url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=10)

        exchange = await self._channel.declare_exchange(
            self.exchange_name,
            ExchangeType.TOPIC,
            durable=True,
        )

        self._queue = await self._channel.declare_queue(
            self.QUEUE_NAME,
            durable=True,
        )

        await self._queue.bind(exchange, routing_key="order.created")
        await self._queue.bind(exchange, routing_key="order.cancelled")

        self._consume_tag = await self._queue.consume(self._on_message, no_ack=False)
        self._started = True

        logger.info(
            "KitchenEventConsumer started: queue=%s exchange=%s",
            self.QUEUE_NAME,
            self.exchange_name,
        )

    async def close(self) -> None:
        if self._queue and self._consume_tag:
            try:
                await self._queue.cancel(self._consume_tag)
            except Exception:
                logger.exception("Failed to cancel kitchen consumer")

        if self._channel:
            try:
                await self._channel.close()
            except Exception:
                logger.exception("Failed to close kitchen channel")

        if self._connection:
            try:
                await self._connection.close()
            except Exception:
                logger.exception("Failed to close kitchen connection")

        self._started = False
        self._consume_tag = None
        self._queue = None
        self._channel = None
        self._connection = None

    async def _on_message(self, message: IncomingMessage) -> None:
        async with message.process(requeue=False):
            try:
                envelope = json.loads(message.body.decode())
                event_name = envelope.get("event_name")
                data = envelope.get("data") or envelope.get("payload") or {}
                metadata = envelope.get("metadata") or {}

                correlation_id = self._extract_correlation_id(
                    message,
                    envelope,
                    metadata,
                )

                if event_name == "order.created":
                    await self._handle_order_created(data, correlation_id, envelope)
                elif event_name == "order.cancelled":
                    await self._handle_order_cancelled(data, correlation_id, envelope)
                else:
                    logger.info("Skipping unsupported event_name=%s", event_name)
            except Exception:
                logger.exception("Failed to process message in KitchenEventConsumer")

    async def _handle_order_created(
        self,
        data: dict[str, Any],
        correlation_id: str | None,
        envelope: dict[str, Any],
    ) -> None:
        # Поскольку order_service шлёт плоский envelope без payload/data,
        # достаём поля прямо из envelope, с fallback на data.
        order_id = (
            envelope.get("order_id")
            or data.get("order_id")
            or envelope.get("aggregate_id")
            or data.get("id")
        )
        store_id = envelope.get("store_id") or data.get("store_id")
        address_id = envelope.get("address_id") or data.get("address_id")
        customer_id = envelope.get("customer_id") or data.get("customer_id")
        items = envelope.get("items") or data.get("items") or []

        if order_id is None or store_id is None or address_id is None:
            logger.warning(
                "order.created missing fields: %s",
                {
                    "order_id": order_id,
                    "store_id": store_id,
                    "address_id": address_id,
                },
            )
            return

        async with async_session() as session:
            dao = KitchenDAO(session)
            await dao.create_kitchen_job_from_order(
                order_id=int(order_id),
                store_id=int(store_id),
                address_id=int(address_id),
                customer_id=int(customer_id) if customer_id is not None else None,
                items=items,
                correlation_id=correlation_id,
            )
            await session.commit()

        logger.info(
            "Kitchen job created for order_id=%s (store_id=%s, customer_id=%s)",
            order_id,
            store_id,
            customer_id,
        )
    @staticmethod
    def _extract_correlation_id(
        message: IncomingMessage,
        envelope: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        if message.correlation_id:
            return str(message.correlation_id)

        headers = message.headers or {}
        if "x-correlation-id" in headers:
            return str(headers["x-correlation-id"])

        metadata = metadata or envelope.get("metadata") or {}
        if "correlation_id" in metadata:
            return str(metadata["correlation_id"])

        if "correlation_id" in envelope:
            return str(envelope["correlation_id"])

        return None