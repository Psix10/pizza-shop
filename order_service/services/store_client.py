import os
from typing import Any

import httpx

from common.correlation import CORRELATION_HEADER


STORE_SERVICE_URL = os.getenv(
    "STORE_SERVICE_URL",
    "http://store_service_pizza:8004",
)


def _build_headers(correlation_id: str | None = None) -> dict[str, str]:
    headers: dict[str, str] = {}
    if correlation_id:
        headers[CORRELATION_HEADER] = correlation_id
    return headers


async def get_store(
    store_id: int,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    url = f"{STORE_SERVICE_URL}/stores/{store_id}"
    async with httpx.AsyncClient(
        headers=_build_headers(correlation_id),
        timeout=5.0,
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


async def get_nearest_store(
    lat: float,
    lng: float,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    url = f"{STORE_SERVICE_URL}/stores/nearest"
    async with httpx.AsyncClient(
        headers=_build_headers(correlation_id),
        timeout=5.0,
    ) as client:
        resp = await client.get(
            url,
            params={"lat": lat, "lng": lng},
        )
        resp.raise_for_status()
        return resp.json()


async def get_delivery_zones(
    store_id: int,
    correlation_id: str | None = None,
) -> list[dict[str, Any]]:
    url = f"{STORE_SERVICE_URL}/stores/{store_id}/delivery-zones"
    async with httpx.AsyncClient(
        headers=_build_headers(correlation_id),
        timeout=5.0,
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()