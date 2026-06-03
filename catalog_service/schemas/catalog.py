from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sort_order: int
    is_active: bool


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    name: str
    description: str | None = None
    image_url: str | None = None
    is_active: bool


# На будущее для админки (CRUD):
class CategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    sort_order: int = 0
    is_active: bool = True


class CategoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: int
    name: str
    description: str | None = None
    image_url: str | None = None
    is_active: bool = True


class ProductUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: int | None = None
    name: str | None = None
    description: str | None = None
    image_url: str | None = None
    is_active: bool | None = None


class ProductVariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    size: str
    sku: str
    base_price: float
    weight_g: int | None = None
    is_active: bool