from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.db import get_session
from dao.store_dao import StoreDAO
from schemas.store import StoreRead, DeliveryZoneRead

router = APIRouter(prefix="/stores", tags=["stores"])


def get_store_dao(session: AsyncSession = Depends(get_session)) -> StoreDAO:
    return StoreDAO(session)


@router.get("/nearest", response_model=StoreRead)
async def get_nearest_store(
    lat: float = Query(...),
    lng: float = Query(...),
    dao: StoreDAO = Depends(get_store_dao),
):
    store = await dao.find_nearest_store(lat, lng)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active stores",
        )
    return store


@router.get("/{store_id}", response_model=StoreRead)
async def get_store(
    store_id: int,
    dao: StoreDAO = Depends(get_store_dao),
):
    store = await dao.get_store(store_id)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )
    return store


@router.get("/{store_id}/delivery-zones", response_model=list[DeliveryZoneRead])
async def get_delivery_zones(
    store_id: int,
    dao: StoreDAO = Depends(get_store_dao),
):
    store = await dao.get_store(store_id)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )
    zones = await dao.list_delivery_zones(store_id)
    return zones