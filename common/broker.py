import json
import os

import aio_pika


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE", "domain_events")


class RabbitBroker:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None

    async def connect(self):
        if self.connection:
            return

        self.connection = await aio_pika.connect_robust(RABBITMQ_URL)
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(
            RABBITMQ_EXCHANGE,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

    async def publish(self, routing_key: str, payload: dict, headers: dict | None = None):
        await self.connect()
        body = json.dumps(payload, default=str).encode()

        message = aio_pika.Message(
            body=body,
            headers=headers or {},
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        await self.exchange.publish(message, routing_key=routing_key)

    async def close(self):
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()