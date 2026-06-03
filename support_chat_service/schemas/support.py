from datetime import datetime

from pydantic import BaseModel


class SupportMessageCreate(BaseModel):
    message_text: str
    attachment_url: str | None = None


class SupportMessageRead(BaseModel):
    id: int
    thread_id: int
    sender_id: int
    sender_role: str
    message_text: str
    attachment_url: str | None = None
    created_at: datetime
    is_read: bool

    model_config = {"from_attributes": True}


class SupportThreadCreate(BaseModel):
    order_id: int | None = None
    priority: str = "normal"
    message_text: str


class SupportThreadRead(BaseModel):
    id: int
    customer_id: int
    order_id: int | None = None
    status: str
    priority: str
    created_at: datetime
    closed_at: datetime | None = None

    model_config = {"from_attributes": True}


class SupportThreadDetailRead(SupportThreadRead):
    messages: list[SupportMessageRead]