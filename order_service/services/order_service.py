import json
from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession

from dao.order_dao import OrderDAO
from dao.outbox_dao import OutboxDAO
from models.outbox import OutboxEvent
from common.correlation import get_correlation_id


class OrderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_dao = OrderDAO(session)
        self.outbox_dao = OutboxDAO(session)

    async def checkout(self, command: CheckoutCommand) -> OrderDTO:
        # 1. создаём заказ и связанные сущности в одной транзакции
        order = await self.order_dao.create_order_from_checkout(command)

        # 2. формируем payload для события order.created
        payload = {
            "order_id": str(order.id),
            "customer_id": str(order.customer_id),
            "store_id": str(order.store_id),
            "status": order.status.value,
            "total_amount": order.total_amount,
            "promised_at": order.promised_at,
            "items": [
                {
                    "product_variant_id": str(item.product_variant_id),
                    "qty": item.qty,
                    "unit_price": item.unit_price,
                }
                for item in order.items
            ],
        }

        metadata = {
            "correlation_id": get_correlation_id(),
            "source_service": "order_service",
            "schema_version": "1",
        }

        outbox_event = OutboxEvent(
            aggregate_type="order",
            aggregate_id=str(order.id),
            event_name="order.created",
            payload_json=json.dumps(
                {
                    "payload": payload,
                    "metadata": metadata,
                },
                default=str,
            ),
            status="pending",
            created_at=datetime.now(UTC),
        )

        await self.outbox_dao.save(outbox_event)

        # 3. commit в вызывающем коде/роутере (чтобы заказ и событие закоммитились вместе)
        return OrderDTO.from_model(order)