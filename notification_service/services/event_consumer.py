import json

import aio_pika
from sqlalchemy.ext.asyncio import async_sessionmaker

from common.broker import RABBITMQ_EXCHANGE, RABBITMQ_URL
from dao.notification_dao import NotificationDAO
from schemas.notification import NotificationEventIn


class NotificationEventConsumer:
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
            "notification.order.created",
            durable=True,
        )
        await self.queue.bind(exchange, routing_key="order.created")
        await self.queue.consume(self.handle_order_created)

    async def handle_order_created(self, message: aio_pika.IncomingMessage):
        async with message.process():
            payload = json.loads(message.body.decode())

            recipient_user_id = payload.get("customer_id")
            if recipient_user_id is None:
                return

            event = NotificationEventIn(
                event_type="order.created",
                recipient_user_id=recipient_user_id,
                channel="in_app",
                payload=payload,
            )

            async with self.session_factory() as session:
                dao = NotificationDAO(session)
                await dao.enqueue_notification(event)
                await session.commit()

    async def close(self):
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()