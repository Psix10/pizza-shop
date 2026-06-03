# schemas/profile.py
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from datetime import date

class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    user_id: int
    avatar_url: str | None = None
    birth_date: date | None = None
    email: str | None = None
    phone: str | None = None
    messenger: str | None = None


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    avatar_url: str | None = None
    birth_date: datetime | None = None


class AddressRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str | None
    city: str
    street: str
    house: str
    apartment: str | None
    entrance: str | None
    floor: str | None
    door_code: str | None
    lat: float | None
    lng: float | None
    is_default: bool


class AddressCreateRequest(BaseModel):
    label: str | None = None
    city: str
    street: str
    house: str
    apartment: str | None = None
    entrance: str | None = None
    floor: str | None = None
    door_code: str | None = None
    lat: float | None = None
    lng: float | None = None
    is_default: bool = False


class AddressUpdateRequest(BaseModel):
    label: str | None = None
    city: str | None = None
    street: str | None = None
    house: str | None = None
    apartment: str | None = None
    entrance: str | None = None
    floor: str | None = None
    door_code: str | None = None
    lat: float | None = None
    lng: float | None = None
    is_default: bool | None = None


class ContactsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    phone: str | None = None
    messenger: str | None = None
    avatar_url: str | None = None
    birth_date: date | None = None


class ContactsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    phone: str | None = None
    messenger: str | None = None
    avatar_url: str | None = None
    birth_date: date | None = None