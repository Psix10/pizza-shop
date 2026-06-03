from __future__ import annotations

import json
from datetime import datetime, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.notification import NotificationQueue, UserDevice
from schemas.notification import NotificationEventIn


class NotificationDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def enqueue_notification(self, data: NotificationEventIn) -> NotificationQueue:
        item = NotificationQueue(
            recipient_user_id=data.recipient_user_id,
            channel=data.channel,
            event_type=data.event_type,
            payload_json=json.dumps(data.payload, default=str),
            status="pending",
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def list_notifications_for_user(self, user_id: int) -> list[NotificationQueue]:
        stmt = (
            select(NotificationQueue)
            .where(NotificationQueue.recipient_user_id == user_id)
            .order_by(NotificationQueue.scheduled_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def lock_pending_notifications(self, limit: int = 50) -> list[NotificationQueue]:
        stmt = (
            select(NotificationQueue)
            .where(NotificationQueue.status == "pending")
            .order_by(NotificationQueue.id.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_as_sent(self, item: NotificationQueue) -> None:
        item.status = "sent"
        item.sent_at = datetime.now(UTC)
        item.error_message = None
        await self.session.flush()

    async def mark_as_failed(self, item: NotificationQueue, error_message: str | None = None) -> None:
        item.status = "failed"
        item.error_message = error_message
        await self.session.flush()

    async def register_device(
        self,
        user_id: int,
        platform: str,
        push_token: str,
    ) -> UserDevice:
        stmt = select(UserDevice).where(UserDevice.push_token == push_token)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.user_id = user_id
            existing.platform = platform
            existing.is_active = True
            await self.session.flush()
            return existing

        device = UserDevice(
            user_id=user_id,
            platform=platform,
            push_token=push_token,
            is_active=True,
        )
        self.session.add(device)
        await self.session.flush()
        return device

    async def list_devices_for_user(self, user_id: int) -> list[UserDevice]:
        stmt = (
            select(UserDevice)
            .where(UserDevice.user_id == user_id)
            .order_by(UserDevice.id.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())