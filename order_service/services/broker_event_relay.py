from common.broker import RabbitBroker
from models.outbox import OutboxEvent


class BrokerEventRelay:
    def __init__(self):
        self.broker = RabbitBroker()

    async def publish(self, event: OutboxEvent, correlation_id: str | None = None) -> None:
        payload = event.payload_json
        if isinstance(payload, str):
            import json
            payload = json.loads(payload)

        headers = {}
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id

        await self.broker.publish(
            routing_key=event.event_name,
            payload=payload,
            headers=headers,
        )