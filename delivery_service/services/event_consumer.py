from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import aio_pika
from aio_pika import ExchangeType, IncomingMessage

from db.db import async_session
from dao.delivery_dao import DeliveryDAO
from schemas.delivery import DeliveryJobCreateInternal
from services.order_client import update_order_status

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE", "domain_events")
DELIVERY_QUEUE_NAME = os.getenv("DELIVERY_QUEUE_NAME", "delivery.events")

ORDER_CREATED_ROUTING_KEY = os.getenv("ORDER_CREATED_ROUTING_KEY", "order.created")
KITCHEN_ORDER_READY_ROUTING_KEY = os.getenv(
    "KITCHEN_ORDER_READY_ROUTING_KEY",
    "kitchen.order.ready",
)


class DeliveryEventConsumer:
    def __init__(self) -> None:
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.abc.AbstractRobustChannel | None = None
        self._queue: aio_pika.abc.AbstractQueue | None = None
        self._consume_tag: str | None = None
        self._started = False

    async def start(self) -> None:
        if self._started:
            return

        self._connection = await aio_pika.connect_robust(RABBITMQ_URL)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=10)

        exchange = await self._channel.declare_exchange(
            RABBITMQ_EXCHANGE,
            ExchangeType.TOPIC,
            durable=True,
        )

        self._queue = await self._channel.declare_queue(
            DELIVERY_QUEUE_NAME,
            durable=True,
        )

        await self._queue.bind(exchange, routing_key=ORDER_CREATED_ROUTING_KEY)
        await self._queue.bind(exchange, routing_key=KITCHEN_ORDER_READY_ROUTING_KEY)

        self._consume_tag = await self._queue.consume(self._on_message)
        self._started = True

        logger.info(
            "DeliveryEventConsumer started: queue=%s exchange=%s routing_keys=[%s,%s]",
            DELIVERY_QUEUE_NAME,
            RABBITMQ_EXCHANGE,
            ORDER_CREATED_ROUTING_KEY,
            KITCHEN_ORDER_READY_ROUTING_KEY,
        )

    async def close(self) -> None:
        if self._queue and self._consume_tag:
            try:
                await self._queue.cancel(self._consume_tag)
            except Exception:
                logger.exception("Failed to cancel consumer")

        if self._channel:
            try:
                await self._channel.close()
            except Exception:
                logger.exception("Failed to close RabbitMQ channel")

        if self._connection:
            try:
                await self._connection.close()
            except Exception:
                logger.exception("Failed to close RabbitMQ connection")

        self._started = False
        self._consume_tag = None
        self._queue = None
        self._channel = None
        self._connection = None

    async def _on_message(self, message: IncomingMessage) -> None:
        async with message.process():
            envelope = self._decode_message(message)

            event_name = envelope.get("event_name")
            data = envelope.get("data") or envelope.get("payload") or {}
            metadata = envelope.get("metadata") or {}

            correlation_id = self._extract_correlation_id(message, envelope, metadata)

            if event_name == "order.created":
                await self._handle_order_created(data, correlation_id, envelope)
            elif event_name == "kitchen.order.ready":
                await self._handle_kitchen_order_ready(data, correlation_id, envelope)
            else:
                logger.info("Skipping unsupported event_name=%s", event_name)
                return

    async def _handle_order_created(
        self,
        data: dict[str, Any],
        correlation_id: str | None,
        envelope: dict[str, Any],
    ) -> None:
        order_id = (
            envelope.get("order_id")
            or data.get("order_id")
            or envelope.get("aggregate_id")
            or data.get("id")
        )

        if order_id is None:
            logger.warning("order.created without order_id: %s", envelope)
            return

        logger.info(
            "Received order.created for order_id=%s correlation_id=%s",
            order_id,
            correlation_id,
        )

        await update_order_status(
            order_id=int(order_id),
            status_value="delivery_pending",
            changed_by=None,
            correlation_id=correlation_id,
        )

        logger.info("Order %s marked as delivery_pending", order_id)

    async def _handle_kitchen_order_ready(
        self,
        data: dict[str, Any],
        correlation_id: str | None,
        envelope: dict[str, Any],
    ) -> None:
        # kitchen.order.ready приходит от outbox кухни в формате:
        # { "payload": { order_id, store_id, address_id, priority_score }, "metadata": {...} }
        payload = envelope.get("payload") or data

        order_id = (
            payload.get("order_id")
            or envelope.get("order_id")
            or envelope.get("aggregate_id")
            or data.get("order_id")
        )
        store_id = payload.get("store_id")
        address_id = payload.get("address_id")
        priority_score = payload.get("priority_score")

        if order_id is None or store_id is None or address_id is None:
            logger.warning(
                "kitchen.order.ready missing fields: %s",
                {"order_id": order_id, "store_id": store_id, "address_id": address_id},
            )
            return

        logger.info(
            "Received kitchen.order.ready for order_id=%s correlation_id=%s",
            order_id,
            correlation_id,
        )

        async with async_session() as session:
            dao = DeliveryDAO(session)

            job_data = DeliveryJobCreateInternal(
                order_id=int(order_id),
                store_id=int(store_id),
                address_id=int(address_id),
                customer_id=payload.get("customer_id"),
                priority_score=priority_score,
            )

            job = await dao.create_delivery_job(job_data)
            await session.commit()

        await update_order_status(
            order_id=int(order_id),
            status_value="delivery_assigned",  # подгони под свои статусы, если надо
            changed_by=None,
            correlation_id=correlation_id,
        )

        logger.info(
            "DeliveryJob created id=%s for order_id=%s (status=%s)",
            job.id,
            order_id,
            job.status,
        )

    @staticmethod
    def _decode_message(message: IncomingMessage) -> dict[str, Any]:
        try:
            return json.loads(message.body.decode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to decode RabbitMQ message body")
            raise ValueError("Invalid message body") from exc

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