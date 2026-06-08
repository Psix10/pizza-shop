from datetime import datetime
from typing import Any
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

class NotificationRead(BaseModel):
    id: int
    recipient_user_id: int | None
    channel: str
    message_text: str | None = None
    template_code: str | None = None
    status: str
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    metadata: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class NotificationCreateInternal(BaseModel):
    recipient_user_id: int | None
    channel: str  # "push" / "email" / "sms"
    template_code: str | None = None
    message_text: str | None = None
    metadata: dict[str, Any] | None = None


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