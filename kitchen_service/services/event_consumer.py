import json

import aio_pika
from sqlalchemy.ext.asyncio import async_sessionmaker

from common.broker import RABBITMQ_EXCHANGE, RABBITMQ_URL
from dao.kitchen_dao import KitchenDAO
from schemas.events import OrderCreatedEvent


class KitchenEventConsumer:
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        self.connection = None
        self.channel = None
        self.queue = None

    async def start(self):
        self.connection = await aio_pika.connect_robust(RABBITMQ_URL)
        self.channel = await self.connection.channel()
        exchange = await self.channel.declare_exchange(
            RABBITMQ_EXCHANGE,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

        self.queue = await self.channel.declare_queue(
            "kitchen.order.created",
            durable=True,
        )
        await self.queue.bind(exchange, routing_key="order.created")
        await self.queue.consume(self.handle_order_created)

    async def handle_order_created(self, message: aio_pika.IncomingMessage):
        async with message.process():
            payload = json.loads(message.body.decode())
            event = OrderCreatedEvent(**payload)

            async with self.session_factory() as session:
                dao = KitchenDAO(session)
                await dao.create_job_from_order_created(event)
                await session.commit()

    async def close(self):
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()