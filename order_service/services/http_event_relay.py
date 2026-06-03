# services/http_event_relay.py
from __future__ import annotations

import json
import os

import httpx

from models.outbox import OutboxEvent

KITCHEN_SERVICE_URL = os.getenv(
    "KITCHEN_SERVICE_URL",
    "http://kitchen_service_pizza:8005",
)


class HttpEventRelay:
    async def publish(self, event: OutboxEvent) -> None:
        payload = json.loads(event.payload_json)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{KITCHEN_SERVICE_URL}/internal/events/order-created",
                json=payload,
                timeout=5.0,
            )
            resp.raise_for_status()