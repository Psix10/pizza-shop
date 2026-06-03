from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class OrderCreatedItemEvent(BaseModel):
    product_variant_id: int
    product_name: str
    variant_name: str | None = None
    qty: int
    unit_price: Decimal


class OrderCreatedEvent(BaseModel):
    event_name: str
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