from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.db import get_session
from dao.support_dao import SupportDAO
from schemas.support import (
    SupportMessageCreate,
    SupportMessageRead,
    SupportThreadCreate,
    SupportThreadDetailRead,
    SupportThreadRead,
)

router = APIRouter(prefix="/support/threads", tags=["support"])


def get_current_customer_id() -> int:
    return 1


def get_support_dao(session: AsyncSession = Depends(get_session)) -> SupportDAO:
    return SupportDAO(session)


@router.get("", response_model=list[SupportThreadRead])
async def list_threads(
    customer_id: int = Depends(get_current_customer_id),
    dao: SupportDAO = Depends(get_support_dao),
):
    return await dao.list_threads_for_customer(customer_id)


@router.post("", response_model=SupportThreadDetailRead, status_code=status.HTTP_201_CREATED)
async def create_thread(
    data: SupportThreadCreate,
    customer_id: int = Depends(get_current_customer_id),
    session: AsyncSession = Depends(get_session),
    dao: SupportDAO = Depends(get_support_dao),
):
    thread = await dao.create_thread(
        customer_id=customer_id,
        order_id=data.order_id,
        priority=data.priority,
        message_text=data.message_text,
    )
    await session.commit()
    return thread


@router.get("/{thread_id}", response_model=SupportThreadDetailRead)
async def get_thread(
    thread_id: int,
    customer_id: int = Depends(get_current_customer_id),
    dao: SupportDAO = Depends(get_support_dao),
):
    thread = await dao.get_thread_for_customer(thread_id, customer_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


@router.post("/{thread_id}/messages", response_model=SupportMessageRead, status_code=status.HTTP_201_CREATED)
async def create_message(
    thread_id: int,
    data: SupportMessageCreate,
    customer_id: int = Depends(get_current_customer_id),
    session: AsyncSession = Depends(get_session),
    dao: SupportDAO = Depends(get_support_dao),
):
    message = await dao.add_message(
        thread_id=thread_id,
        customer_id=customer_id,
        message_text=data.message_text,
        attachment_url=data.attachment_url,
    )
    if not message:
        raise HTTPException(status_code=404, detail="Thread not found or closed")

    await session.commit()
    return message


@router.post("/{thread_id}/close", response_model=SupportThreadRead)
async def close_thread(
    thread_id: int,
    customer_id: int = Depends(get_current_customer_id),
    session: AsyncSession = Depends(get_session),
    dao: SupportDAO = Depends(get_support_dao),
):
    thread = await dao.close_thread(thread_id, customer_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    await session.commit()
    return thread