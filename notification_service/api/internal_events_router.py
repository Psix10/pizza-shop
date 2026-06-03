from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.db import get_session
from dao.notification_dao import NotificationDAO
from schemas.notification import NotificationEventIn, NotificationQueueRead


router = APIRouter(prefix="/internal/events", tags=["internal-events"])


def get_notification_dao(session: AsyncSession = Depends(get_session)) -> NotificationDAO:
    return NotificationDAO(session)


@router.post("/notify", response_model=NotificationQueueRead, status_code=status.HTTP_201_CREATED)
async def notify(
    data: NotificationEventIn,
    session: AsyncSession = Depends(get_session),
    dao: NotificationDAO = Depends(get_notification_dao),
):
    item = await dao.enqueue_notification(data)
    await session.commit()
    return item