from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.idempotency import IdempotencyKey


class IdempotencyDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_key(
        self,
        customer_id: int,
        key: str,
        operation: str,
    ) -> IdempotencyKey | None:
        stmt = select(IdempotencyKey).where(
            IdempotencyKey.customer_id == customer_id,
            IdempotencyKey.key == key,
            IdempotencyKey.operation == operation,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_key(
        self,
        customer_id: int,
        key: str,
        operation: str,
    ) -> IdempotencyKey:
        record = IdempotencyKey(
            customer_id=customer_id,
            key=key,
            operation=operation,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def attach_order(
        self,
        record: IdempotencyKey,
        order_id: int,
    ) -> None:
        record.order_id = order_id
        await self.session.flush()