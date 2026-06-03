# schemas/auth.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class RegisterCustomerRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: str | None = None


class RegisterEmployeeRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: str | None = None
    role: str  # 'cook' или 'courier'


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_id: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str
    device_id: str | None = None


class LogoutRequest(BaseModel):
    refresh_token: str
    device_id: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None = None
    role_name: str | None = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str
    new_password: str


class ChangeEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_email: EmailStr