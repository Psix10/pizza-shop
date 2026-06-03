from __future__ import annotations

from math import radians, cos, sin, asin, sqrt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.store import Store, DeliveryZone


class StoreDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_store(self, store_id: int) -> Store | None:
        stmt = select(Store).where(Store.id == store_id, Store.is_active.is_(True))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_delivery_zones(self, store_id: int) -> list[DeliveryZone]:
        stmt = select(DeliveryZone).where(DeliveryZone.store_id == store_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_active_stores(self) -> list[Store]:
        stmt = select(Store).where(Store.is_active.is_(True))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_nearest_store(self, lat: float, lng: float) -> Store | None:
        stores = await self.list_active_stores()
        if not stores:
            return None

        def haversine(lat1, lon1, lat2, lon2) -> float:
            # расстояние в км
            lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
            c = 2 * asin(sqrt(a))
            r = 6371
            return c * r

        nearest = None
        best_distance = None

        for store in stores:
            d = haversine(lat, lng, store.lat, store.lng)
            if best_distance is None or d < best_distance:
                best_distance = d
                nearest = store

        return nearest