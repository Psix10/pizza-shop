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
async def flush_outbox(request: Request):
    dispatcher = request.app.state.outbox_dispatcher
    return await dispatcher.flush_once()