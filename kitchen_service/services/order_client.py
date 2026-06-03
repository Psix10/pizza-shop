import os

import httpx

from common.correlation import CORRELATION_HEADER


ORDER_SERVICE_URL = os.getenv(
    "ORDER_SERVICE_URL",
    "http://order_service_pizza:8005",
)


async def update_order_status(
    order_id: int,
    status: str,
    correlation_id: str | None = None,
) -> dict:
    headers = {}
    if correlation_id:
        headers[CORRELATION_HEADER] = correlation_id

    async with httpx.AsyncClient(headers=headers, timeout=5.0) as client:
        response = await client.patch(
            f"{ORDER_SERVICE_URL}/api/v1/orders/{order_id}/status",
            json={"status": status},
        )
        response.raise_for_status()
        return response.json()