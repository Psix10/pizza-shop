from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class OrderCreatedItemEvent(BaseModel):
    product_variant_id: int
    product_name: str
    variant_name: str | None = None
    qty: int
    unit_price: Decimal


class OrderCreatedEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_name: str = "order.created"
    order_id: int
    order_no: str
    customer_id: int
    store_id: int
    address_id: int
    status: str
    subtotal: Decimal
    delivery_fee: Decimal
    total_amount: Decimal
    placed_at: datetime
    promised_at: datetime | None = None
    items: list[OrderCreatedItemEvent]