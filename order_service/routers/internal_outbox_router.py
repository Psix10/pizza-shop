# routers/internal_outbox_router.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from db.db import get_session
from dao.outbox_dao import OutboxDAO
from services.http_event_relay import HttpEventRelay
from services.broker_event_relay import BrokerEventRelay


router = APIRouter(prefix="/internal/outbox", tags=["internal-outbox"])


def get_outbox_dao(session: AsyncSession = Depends(get_session)) -> OutboxDAO:
    return OutboxDAO(session)


def get_http_event_relay() -> HttpEventRelay:
    return HttpEventRelay()

def get_broker_event_relay() -> BrokerEventRelay:
    return BrokerEventRelay()


@router.post("/flush")
async def flush_outbox(
    request: Request,
    session: AsyncSession = Depends(get_session),
    outbox_dao: OutboxDAO = Depends(get_outbox_dao),
    relay: BrokerEventRelay = Depends(get_broker_event_relay),
):
    events = await outbox_dao.lock_pending_events(limit=50)

    published = 0
    failed = 0
    correlation_id = getattr(request.state, "correlation_id", None)

    for event in events:
        try:
            await relay.publish(event, correlation_id=correlation_id)
            await outbox_dao.mark_as_published(event)
            published += 1
        except Exception as e:
            await outbox_dao.mark_as_failed(event, str(e))
            failed += 1

    await session.commit()
    return {
        "processed": len(events),
        "published": published,
        "failed": failed,
    }