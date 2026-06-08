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
    cancelled_at: datetime | None = None
    priority_score: int | None = None

    model_config = {"from_attributes": True}


class DeliveryJobCreateInternal(BaseModel):
    order_id: int
    store_id: int
    address_id: int
    customer_id: int | None = None
    priority_score: int | None = None