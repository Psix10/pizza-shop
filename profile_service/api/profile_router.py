# api/profile_router.py
from fastapi import APIRouter, Depends

from sqlalchemy.ext.asyncio import AsyncSession

from db.db import get_session
from api.dependencies import get_current_user_id
from dao.profile_dao import ProfileDAO
from schemas.profile import (
    ProfileRead,
    ProfileUpdateRequest,
    AddressRead,
    AddressCreateRequest,
    AddressUpdateRequest,
    ContactsRead,
    ContactsUpdateRequest,
)

router = APIRouter(prefix="/profiles", tags=["profiles"])


def get_profile_dao(session: AsyncSession = Depends(get_session)) -> ProfileDAO:
    return ProfileDAO(session)


@router.get("/me", response_model=ProfileRead)
async def get_me(
    user_id: int = Depends(get_current_user_id),
    dao: ProfileDAO = Depends(get_profile_dao),
):
    profile = await dao.get_or_create_profile(user_id)
    return profile


@router.patch("/me", response_model=ProfileRead)
async def update_me(
    data: ProfileUpdateRequest,
    user_id: int = Depends(get_current_user_id),
    dao: ProfileDAO = Depends(get_profile_dao),
):
    profile = await dao.get_or_create_profile(user_id)
    if data.first_name is not None:
        profile.first_name = data.first_name
    if data.last_name is not None:
        profile.last_name = data.last_name
    if data.avatar_url is not None:
        profile.avatar_url = data.avatar_url
    if data.birth_date is not None:
        profile.birth_date = data.birth_date
    return profile


@router.get("/me/addresses", response_model=list[AddressRead])
async def list_addresses(
    user_id: int = Depends(get_current_user_id),
    dao: ProfileDAO = Depends(get_profile_dao),
):
    addresses = await dao.get_addresses(user_id)
    return addresses


@router.post("/me/addresses", response_model=AddressRead, status_code=201)
async def create_address(
    data: AddressCreateRequest,
    user_id: int = Depends(get_current_user_id),
    dao: ProfileDAO = Depends(get_profile_dao),
):
    addr = await dao.create_address(
        user_id=user_id,
        label=data.label,
        city=data.city,
        street=data.street,
        house=data.house,
        apartment=data.apartment,
        entrance=data.entrance,
        floor=data.floor,
        door_code=data.door_code,
        lat=data.lat,
        lng=data.lng,
        is_default=data.is_default,
    )
    return addr

@router.patch("/me/addresses/{address_id}", response_model=AddressRead)
async def update_address(
    address_id: int,
    data: AddressUpdateRequest,
    user_id: int = Depends(get_current_user_id),
    dao: ProfileDAO = Depends(get_profile_dao),
):
    update_data = data.model_dump(exclude_unset=True)
    addr = await dao.update_address(user_id, address_id, update_data)
    return addr


@router.delete("/me/addresses/{address_id}", status_code=204)
async def delete_address(
    address_id: int,
    user_id: int = Depends(get_current_user_id),
    dao: ProfileDAO = Depends(get_profile_dao),
):
    await dao.delete_address(user_id, address_id)
    return

@router.get("/me/contacts", response_model=ContactsRead)
async def get_contacts(
    user_id: int = Depends(get_current_user_id),
    dao: ProfileDAO = Depends(get_profile_dao),
):
    profile = await dao.get_contacts(user_id)
    return ContactsRead(
        phone=profile.phone,
        messenger=profile.messenger,
    )


@router.put("/me/contacts", response_model=ContactsRead)
async def update_contacts(
    data: ContactsUpdateRequest,
    user_id: int = Depends(get_current_user_id),
    dao: ProfileDAO = Depends(get_profile_dao),
):
    profile = await dao.update_contacts(user_id, data)
    return ContactsRead(
        phone=profile.phone,
        messenger=profile.messenger,
        avatar_url=profile.avatar_url,
        birth_date=profile.birth_date,
    )
