from datetime import time
from pydantic import BaseModel, ConfigDict


class StoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str | None = None
    address: str
    lat: float
    lng: float
    timezone: str


class DeliveryZoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    zone_name: str
    polygon_geojson: str
    min_eta: int
    max_eta: int