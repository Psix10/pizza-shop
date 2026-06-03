import asyncio
import json
import logging
import os
from typing import Any

import aio_pika
from aio_pika import ExchangeType, IncomingMessage

from services.order_client import update_order_status

logger = logging.getLogger(__name__)


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE", "domain_events")
DELIVERY_QUEUE_NAME = os.getenv("DELIVERY_QUEUE_NAME", "delivery.order_created")
ORDER_CREATED_ROUTING_KEY = os.getenv("ORDER_CREATED_ROUTING_KEY", "order.created")


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
        self._consume_tag = await self._queue.consume(self._on_message)
        self._started = True

        logger.info(
            "DeliveryEventConsumer started: queue=%s exchange=%s routing_key=%s",
            DELIVERY_QUEUE_NAME,
            RABBITMQ_EXCHANGE,
            ORDER_CREATED_ROUTING_KEY,
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
            payload = self._decode_message(message)

            event_name = payload.get("event_name")
            if event_name and event_name != "order.created":
                logger.info("Skipping unsupported event_name=%s", event_name)
                return

            order_id = payload.get("order_id") or payload.get("id")
            correlation_id = self._extract_correlation_id(message, payload)

            if order_id is None:
                logger.warning("Received message without order_id: %s", payload)
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
        payload: dict[str, Any],
    ) -> str | None:
        if message.correlation_id:
            return str(message.correlation_id)

        headers = message.headers or {}
        if "x-correlation-id" in headers:
            return str(headers["x-correlation-id"])

        if "correlation_id" in payload:
            return str(payload["correlation_id"])

        return None