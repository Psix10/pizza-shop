from datetime import datetime
from pydantic import BaseModel


class NotificationEventIn(BaseModel):
    event_type: str
    recipient_user_id: int
    channel: str = "in_app"
    payload: dict


class NotificationQueueRead(BaseModel):
    id: int
    recipient_user_id: int
    channel: str
    event_type: str
    payload_json: str
    status: str
    scheduled_at: datetime
    sent_at: datetime | None = None
    error_message: str | None = None

    model_config = {"from_attributes": True}


class UserDeviceCreate(BaseModel):
    platform: str
    push_token: str


class UserDeviceRead(BaseModel):
    id: int
    user_id: int
    platform: str
    push_token: str
    is_active: bool

    model_config = {"from_attributes": True}