from fastapi import Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from dao.idempotency_dao import IdempotencyDAO
from db.db import get_session

async def get_current_customer_id(
    x_user_id: str | None = Header(default=None),
) -> int:
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="x-user-id header missing",
        )
    try:
        return int(x_user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid x-user-id header",
        )
        
def get_idempotency_dao(session: AsyncSession = Depends(get_session)) -> IdempotencyDAO:
    return IdempotencyDAO(session)