from datetime import datetime, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.support import SupportMessage, SupportThread


class SupportDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_threads_for_customer(self, customer_id: int) -> list[SupportThread]:
        stmt = (
            select(SupportThread)
            .where(SupportThread.customer_id == customer_id)
            .order_by(SupportThread.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_thread_for_customer(self, thread_id: int, customer_id: int) -> SupportThread | None:
        stmt = (
            select(SupportThread)
            .where(SupportThread.id == thread_id, SupportThread.customer_id == customer_id)
            .options(selectinload(SupportThread.messages))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_thread(
        self,
        customer_id: int,
        order_id: int | None,
        priority: str,
        message_text: str,
    ) -> SupportThread:
        thread = SupportThread(
            customer_id=customer_id,
            order_id=order_id,
            priority=priority,
            status="open",
        )
        self.session.add(thread)
        await self.session.flush()

        message = SupportMessage(
            thread_id=thread.id,
            sender_id=customer_id,
            sender_role="customer",
            message_text=message_text,
        )
        self.session.add(message)
        await self.session.flush()

        return await self.get_thread_for_customer(thread.id, customer_id)

    async def add_message(
        self,
        thread_id: int,
        customer_id: int,
        message_text: str,
        attachment_url: str | None = None,
    ) -> SupportMessage | None:
        thread = await self.get_thread_for_customer(thread_id, customer_id)
        if not thread or thread.status == "closed":
            return None

        message = SupportMessage(
            thread_id=thread_id,
            sender_id=customer_id,
            sender_role="customer",
            message_text=message_text,
            attachment_url=attachment_url,
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def close_thread(self, thread_id: int, customer_id: int) -> SupportThread | None:
        thread = await self.get_thread_for_customer(thread_id, customer_id)
        if not thread:
            return None

        if thread.status == "closed":
            return thread

        thread.status = "closed"
        thread.closed_at = datetime.now(UTC)
        await self.session.flush()
        return thread