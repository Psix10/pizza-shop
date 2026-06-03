from datetime import datetime
from pydantic import BaseModel


class KitchenJobRead(BaseModel):
    id: int
    order_id: int
    store_id: int
    priority_score: int
    status: str
    queued_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    class Config:
        from_attributes = True