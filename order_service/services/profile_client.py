import os
from typing import Any

import httpx

from common.correlation import CORRELATION_HEADER


PROFILE_SERVICE_URL = os.getenv(
    "PROFILE_SERVICE_URL",
    "http://profile_service_pizza:8002",
)


async def get_address_for_user(
    address_id: int,
    user_id: int,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    url = f"{PROFILE_SERVICE_URL}/profiles/me/addresses"

    headers: dict[str, str] = {
        "x-user-id": str(user_id),
    }
    if correlation_id:
        headers[CORRELATION_HEADER] = correlation_id

    async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        addresses = resp.json()

    for address in addresses:
        if address["id"] == address_id:
            return address

    raise ValueError("Address not found")