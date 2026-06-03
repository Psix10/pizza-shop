import os

import httpx

from common.correlation import CORRELATION_HEADER


DELIVERY_SERVICE_URL = os.getenv(
    "DELIVERY_SERVICE_URL",
    "http://delivery_service_pizza:8007",
)


async def create_delivery_job(
    order_id: int,
    store_id: int,
    address_id: int,
    correlation_id: str | None = None,
) -> dict:
    payload = {
        "order_id": order_id,
        "store_id": store_id,
        "address_id": address_id,
    }

    headers = {}
    if correlation_id:
        headers[CORRELATION_HEADER] = correlation_id

    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            f"{DELIVERY_SERVICE_URL}/api/v1/delivery/jobs/internal",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        return response.json()