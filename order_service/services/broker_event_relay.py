# services/broker_event_relay.py
from __future__ import annotations

import json
import logging
import uuid

import aio_pika

logger = logging.getLogger(__name__)


class BrokerEventRelay:
    def __init__(self, source_service: str, exchange_name: str = "domain_events"):
        self.source_service = source_service
        self.exchange_name = exchange_name
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.abc.AbstractRobustChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    async def _get_exchange(self) -> aio_pika.abc.AbstractExchange:
        if self._exchange is None:
            self._connection = await aio_pika.connect_robust(
                "amqp://guest:guest@rabbitmq:5672/"
            )
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=10)
            self._exchange = await self._channel.declare_exchange(
                self.exchange_name,
                aio_pika.ExchangeType.TOPIC,
                durable=True,
            )
        return self._exchange

    async def publish(self, event) -> None:
        envelope = json.loads(event.payload_json)

        # гарантируем наличие metadata
        metadata = envelope.get("metadata") or {}
        envelope["metadata"] = metadata

        # берём correlation_id из metadata, если есть, иначе генерим новый
        correlation_id = metadata.get("correlation_id") or str(uuid.uuid4())

        metadata.setdefault("source_service", self.source_service)
        metadata.setdefault("schema_version", "1")
        metadata["correlation_id"] = correlation_id

        body = json.dumps(envelope, default=str).encode("utf-8")

        exchange = await self._get_exchange()
        message = aio_pika.Message(
            body=body,
            content_type="application/json",
            correlation_id=correlation_id,
        )

        await exchange.publish(message, routing_key=event.event_name)
        logger.info(
            "Published event %s aggregate_id=%s correlation_id=%s",
            event.event_name,
            event.aggregate_id,
            correlation_id,
        )