from __future__ import annotations

import json
import logging
import os
from typing import Any

import aio_pika
from aio_pika import ExchangeType, IncomingMessage

from db.db import async_session
from dao.notification_dao import NotificationDAO
from schemas.notification import NotificationEventIn

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE", "domain_events")
NOTIFICATION_QUEUE_NAME = os.getenv(
    "NOTIFICATION_QUEUE_NAME",
    "notification.events",
)

ORDER_CREATED_KEY = os.getenv("ORDER_CREATED_ROUTING_KEY", "order.created")
KITCHEN_ORDER_READY_KEY = os.getenv("KITCHEN_ORDER_READY_KEY", "kitchen.order.ready")
DELIVERY_STATUS_UPDATED_KEY = os.getenv(
    "DELIVERY_STATUS_UPDATED_KEY",
    "delivery.status.updated",
)

DELIVERY_PICKED_UP_KEY = os.getenv(
    "DELIVERY_PICKED_UP_KEY",
    "delivery.picked_up",
)
DELIVERY_COMPLETED_KEY = os.getenv(
    "DELIVERY_COMPLETED_KEY",
    "delivery.completed",
)

class NotificationEventConsumer:
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
        await self._channel.set_qos(prefetch_count=20)

        exchange = await self._channel.declare_exchange(
            RABBITMQ_EXCHANGE,
            ExchangeType.TOPIC,
            durable=True,
        )

        self._queue = await self._channel.declare_queue(
            NOTIFICATION_QUEUE_NAME,
            durable=True,
        )

        await self._queue.bind(exchange, routing_key=ORDER_CREATED_KEY)
        await self._queue.bind(exchange, routing_key=KITCHEN_ORDER_READY_KEY)
        await self._queue.bind(exchange, routing_key=DELIVERY_STATUS_UPDATED_KEY)
        await self._queue.bind(exchange, routing_key=DELIVERY_PICKED_UP_KEY)
        await self._queue.bind(exchange, routing_key=DELIVERY_COMPLETED_KEY)

        self._consume_tag = await self._queue.consume(self._on_message)
        self._started = True

        logger.info(
            "NotificationEventConsumer started: queue=%s exchange=%s",
            NOTIFICATION_QUEUE_NAME,
            RABBITMQ_EXCHANGE,
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
        async with message.process(requeue=False):
            try:
                envelope = json.loads(message.body.decode())
                event_name = envelope.get("event_name")
                data = envelope.get("data") or envelope.get("payload") or {}
                metadata = envelope.get("metadata") or {}

                correlation_id = self._extract_correlation_id(message, envelope, metadata)

                if event_name == "order.created":
                    await self._handle_order_created(data, correlation_id, envelope)
                elif event_name == "kitchen.order.ready":
                    await self._handle_kitchen_order_ready(data, correlation_id, envelope)
                elif event_name == "delivery.status.updated":
                    await self._handle_delivery_status_updated(data, correlation_id, envelope)
                elif event_name == "delivery.picked_up":
                    await self._handle_delivery_picked_up(data, correlation_id, envelope)
                elif event_name == "delivery.completed":
                    await self._handle_delivery_completed(data, correlation_id, envelope)
                else:
                    logger.info("Skipping unsupported event_name=%s", event_name)
            except Exception:
                logger.exception("Failed to process message in NotificationEventConsumer")

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
        )
        user_id = envelope.get("customer_id") or data.get("customer_id")

        if order_id is None or user_id is None:
            logger.warning(
                "order.created missing fields for notification: %s",
                envelope,
            )
            return

        event = NotificationEventIn(
            event_type="order.created",
            recipient_user_id=int(user_id),
            channel="in_app",
            payload={
                "order_id": order_id,
                "total_amount": envelope.get("total_amount") or data.get("total_amount"),
                "promised_at": envelope.get("promised_at") or data.get("promised_at"),
                "correlation_id": correlation_id,
            },
        )

        async with async_session() as session:
            dao = NotificationDAO(session)
            await dao.enqueue_notification(event)
            await session.commit()

        logger.info(
            "Enqueued notification (order.created) for user=%s order_id=%s",
            user_id,
            order_id,
        )

    async def _handle_kitchen_order_ready(
        self,
        data: dict[str, Any],
        correlation_id: str | None,
        envelope: dict[str, Any],
    ) -> None:
        order_id = data.get("order_id") or envelope.get("aggregate_id")
        user_id = data.get("customer_id")  # если kitchen будет передавать

        if order_id is None:
            logger.warning("kitchen.order.ready without order_id: %s", envelope)
            return

        event = NotificationEventIn(
            event_type="kitchen.order.ready",
            recipient_user_id=int(user_id) if user_id is not None else 0,
            channel="in_app",
            payload={
                "order_id": order_id,
                "correlation_id": correlation_id,
            },
        )

        async with async_session() as session:
            dao = NotificationDAO(session)
            await dao.enqueue_notification(event)
            await session.commit()

        logger.info(
            "Enqueued notification (kitchen.order.ready) for order_id=%s",
            order_id,
        )

    async def _handle_delivery_status_updated(
        self,
        data: dict[str, Any],
        correlation_id: str | None,
        envelope: dict[str, Any],
    ) -> None:
        order_id = data.get("order_id") or envelope.get("aggregate_id")
        user_id = data.get("customer_id")
        status = data.get("status")

        if order_id is None or status is None:
            logger.warning("delivery.status.updated missing fields: %s", envelope)
            return

        event = NotificationEventIn(
            event_type="delivery.status.updated",
            recipient_user_id=int(user_id) if user_id is not None else 0,
            channel="in_app",
            payload={
                "order_id": order_id,
                "status": status,
                "correlation_id": correlation_id,
            },
        )

        async with async_session() as session:
            dao = NotificationDAO(session)
            await dao.enqueue_notification(event)
            await session.commit()

        logger.info(
            "Enqueued notification (delivery.status.updated) for order_id=%s status=%s",
            order_id,
            status,
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
    
    async def _handle_delivery_picked_up(
        self,
        data: dict[str, Any],
        correlation_id: str | None,
        envelope: dict[str, Any],
    ) -> None:
        order_id = data.get("order_id") or envelope.get("aggregate_id")
        metadata = envelope.get("metadata") or {}
        user_id = metadata.get("customer_id")  # <-- берём из metadata
        delivery_job_id = data.get("delivery_job_id")

        if order_id is None:
            logger.warning("delivery.picked_up without order_id: %s", envelope)
            return

        event = NotificationEventIn(
            event_type="delivery.picked_up",
            recipient_user_id=int(user_id) if user_id is not None else 0,
            channel="in_app",
            payload={
                "order_id": order_id,
                "delivery_job_id": delivery_job_id,
                "correlation_id": correlation_id,
            },
        )

        async with async_session() as session:
            dao = NotificationDAO(session)
            await dao.enqueue_notification(event)
            await session.commit()

        logger.info(
            "Enqueued notification (delivery.picked_up) for order_id=%s user_id=%s",
            order_id,
            user_id,
        )

    async def _handle_delivery_completed(
        self,
        data: dict[str, Any],
        correlation_id: str | None,
        envelope: dict[str, Any],
    ) -> None:
        order_id = data.get("order_id") or envelope.get("aggregate_id")
        metadata = envelope.get("metadata") or {}
        user_id = metadata.get("customer_id")  # <-- тоже из metadata
        delivery_job_id = data.get("delivery_job_id")

        if order_id is None:
            logger.warning("delivery.completed without order_id: %s", envelope)
            return

        event = NotificationEventIn(
            event_type="delivery.completed",
            recipient_user_id=int(user_id) if user_id is not None else 0,
            channel="in_app",
            payload={
                "order_id": order_id,
                "delivery_job_id": delivery_job_id,
                "correlation_id": correlation_id,
            },
        )

        async with async_session() as session:
            dao = NotificationDAO(session)
            await dao.enqueue_notification(event)
            await session.commit()

        logger.info(
            "Enqueued notification (delivery.completed) for order_id=%s user_id=%s",
            order_id,
            user_id,
        )