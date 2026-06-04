# dao/profile_dao.py
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from models.profile import Profile, Address
from schemas.profile import ContactsUpdateRequest

class ProfileDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_profile(self, user_id: int) -> Profile:
        stmt = select(Profile).where(Profile.user_id == user_id)
        profile = await self.session.scalar(stmt)

        if profile is None:
            profile = Profile(
                user_id=user_id,
                avatar_url=None,
                birth_date=None,
                messenger=None,
            )
            self.session.add(profile)
            await self.session.commit()
            await self.session.refresh(profile)

        return profile

    async def get_addresses(self, user_id: int) -> list[Address]:
        stmt = select(Address).where(Address.user_id == user_id)
        result = await self.session.scalars(stmt)
        return list(result)

    async def create_address(
        self,
        user_id: int,
        *,
        label: str | None,
        city: str,
        street: str,
        house: str,
        apartment: str | None,
        entrance: str | None,
        floor: str | None,
        door_code: str | None,
        lat: float | None,
        lng: float | None,
        is_default: bool,
    ) -> Address:
        if is_default:
            # сбросить предыдущий дефолт
            stmt = select(Address).where(
                Address.user_id == user_id,
                Address.is_default.is_(True),
            )
            result = await self.session.scalars(stmt)
            for addr in result:
                addr.is_default = False

        addr = Address(
            user_id=user_id,
            label=label,
            city=city,
            street=street,
            house=house,
            apartment=apartment,
            entrance=entrance,
            floor=floor,
            door_code=door_code,
            lat=lat,
            lng=lng,
            is_default=is_default,
        )
        self.session.add(addr)
        await self.session.flush()
        return addr
    
    async def get_address_by_id_for_user(
        self,
        user_id: int,
        address_id: int,
    ) -> Address | None:
        stmt = select(Address).where(
            Address.id == address_id,
            Address.user_id == user_id,
        )
        return await self.session.scalar(stmt)

    async def update_address(
        self,
        user_id: int,
        address_id: int,
        data: dict,
    ) -> Address:
        addr = await self.get_address_by_id_for_user(user_id, address_id)
        if addr is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found",
            )

        # если устанавливаем is_default=True — сбросить у других
        if data.get("is_default") is True:
            stmt = select(Address).where(
                Address.user_id == user_id,
                Address.is_default.is_(True),
                Address.id != address_id,
            )
            result = await self.session.scalars(stmt)
            for other in result:
                other.is_default = False

        for field, value in data.items():
            if value is not None:
                setattr(addr, field, value)

        await self.session.flush()
        return addr

    async def delete_address(
        self,
        user_id: int,
        address_id: int,
    ) -> None:
        addr = await self.get_address_by_id_for_user(user_id, address_id)
        if addr is None:
            return
        await self.session.delete(addr)
        await self.session.flush()
    
    async def get_contacts(self, user_id: int) -> Profile:
        return await self.get_or_create_profile(user_id)

    async def update_contacts(
        self,
        user_id: int,
        data: ContactsUpdateRequest,
    ) -> Profile:
        profile = await self.get_or_create_profile(user_id)

        if data.messenger is not None:
            profile.messenger = data.messenger
        if data.birth_date is not None:
            profile.birth_date = data.birth_date
        if data.avatar_url is not None:
            profile.avatar_url = data.avatar_url

        await self.session.commit()
        await self.session.refresh(profile)
        return profile