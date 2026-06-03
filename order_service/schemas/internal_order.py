from datetime import datetime
from pydantic import BaseModel


class OrderStatusUpdateInternal(BaseModel):
    status: str
    changed_by: int | None = None
    changed_at: datetime | None = None