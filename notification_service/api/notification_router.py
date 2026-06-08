from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.db import get_session
from dao.notification_dao import NotificationDAO
from schemas.notification import (
    NotificationQueueRead,
    UserDeviceCreate,
    UserDeviceRead,
)


router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_current_user_id() -> int:
    return 0


def get_notification_dao(session: AsyncSession = Depends(get_session)) -> NotificationDAO:
    return NotificationDAO(session)


@router.get("", response_model=list[NotificationQueueRead])
async def list_my_notifications(
    user_id: int = Depends(get_current_user_id),
    dao: NotificationDAO = Depends(get_notification_dao),
):
    return await dao.list_notifications_for_user(user_id)


@router.post("/devices", response_model=UserDeviceRead)
async def register_device(
    data: UserDeviceCreate,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    dao: NotificationDAO = Depends(get_notification_dao),
):
    device = await dao.register_device(
        user_id=user_id,
        platform=data.platform,
        push_token=data.push_token,
    )
    await session.commit()
    return device


@router.get("/devices", response_model=list[UserDeviceRead])
async def list_devices(
    user_id: int = Depends(get_current_user_id),
    dao: NotificationDAO = Depends(get_notification_dao),
):
    return await dao.list_devices_for_user(user_id)


@router.post("/flush")
async def flush_notifications(
    session: AsyncSession = Depends(get_session),
    dao: NotificationDAO = Depends(get_notification_dao),
):
    items = await dao.lock_pending_notifications(limit=50)

    sent = 0
    failed = 0

    for item in items:
        try:
            await dao.mark_as_sent(item)
            sent += 1
        except Exception as e:
            await dao.mark_as_failed(item, str(e))
            failed += 1

    await session.commit()

    return {
        "processed": len(items),
        "sent": sent,
        "failed": failed,
    }