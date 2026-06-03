from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, computed_field


class CartItemCreate(BaseModel):
    product_variant_id: int
    qty: int = 1
    snapshot_json: str | None = None


class CartItemUpdate(BaseModel):
    qty: int


class CartItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_variant_id: int
    qty: int
    unit_price: Decimal
    snapshot_json: str | None = None

class CartRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    status: str
    store_id: int | None = None
    created_at: datetime
    items: list[CartItemRead] = []

    @computed_field
    @property
    def total_amount(self) -> Decimal:
        return sum(item.unit_price * item.qty for item in self.items)