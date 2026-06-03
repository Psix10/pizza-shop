from datetime import datetime

from pydantic import BaseModel


class DeliveryJobRead(BaseModel):
    id: int
    order_id: int
    store_id: int
    address_id: int
    courier_id: int | None = None
    status: str
    assigned_at: datetime
    picked_up_at: datetime | None = None
    delivered_at: datetime | None = None

    model_config = {"from_attributes": True}


class DeliveryJobCreateInternal(BaseModel):
    order_id: int
    store_id: int
    address_id: int