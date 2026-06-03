from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CheckoutCreate(BaseModel):
    address_id: int


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_variant_id: int
    product_name: str
    variant_name: str
    qty: int
    unit_price: float
    modifiers_json: str | None = None


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    customer_id: int
    store_id: int
    address_id: int
    status: str
    subtotal: float
    delivery_fee: float
    total_amount: float
    placed_at: datetime
    promised_at: datetime | None = None
    items: list[OrderItemRead] = Field(default_factory=list)


class OrderStatusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    changed_at: datetime


class OrderShortRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    store_id: int
    status: str
    total_amount: float
    placed_at: datetime