import os
from datetime import UTC, datetime

import httpx

from common.correlation import CORRELATION_HEADER


ORDER_SERVICE_URL = os.getenv(
    "ORDER_SERVICE_URL",
    "http://order_service_pizza:8005",
)


def _build_headers(correlation_id: str | None = None) -> dict[str, str]:
    headers: dict[str, str] = {}
    if correlation_id:
        headers[CORRELATION_HEADER] = correlation_id
    return headers


async def update_order_status(
    order_id: int,
    status_value: str,
    changed_by: int | None = None,
    correlation_id: str | None = None,
) -> dict:
    payload = {
        "status": status_value,
        "changed_by": changed_by,
        "changed_at": datetime.now(UTC).isoformat(),
    }

    async with httpx.AsyncClient(
        headers=_build_headers(correlation_id),
        timeout=5.0,
    ) as client:
        response = await client.post(
            f"{ORDER_SERVICE_URL}/internal/orders/{order_id}/status",
            json=payload,
        )
        response.raise_for_status()
        return response.json()