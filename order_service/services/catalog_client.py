# order_service/services/catalog_client.py
import os
from typing import Any

import httpx

from common.correlation import CORRELATION_HEADER


CATALOG_SERVICE_URL = os.getenv(
    "CATALOG_SERVICE_URL",
    "http://catalog_service_pizza:8003",
)


async def get_product_variant(
    variant_id: int,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    url = f"{CATALOG_SERVICE_URL}/catalog/internal/variants/{variant_id}"

    headers: dict[str, str] = {}
    if correlation_id:
        headers[CORRELATION_HEADER] = correlation_id

    async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()