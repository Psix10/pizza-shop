# notification_service/main.py
from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI

from db.db import init_models
from services.event_consumer import NotificationEventConsumer
from services.dispatcher import NotificationDispatcher

from api.internal_events_router import router as internal_events_router
from api.notification_router import router as notification_router

consumer = NotificationEventConsumer()
dispatcher = NotificationDispatcher()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    task_consumer = asyncio.create_task(consumer.start())
    task_dispatcher = asyncio.create_task(dispatcher.run_forever())
    try:
        yield
    finally:
        task_consumer.cancel()
        task_dispatcher.cancel()


app = FastAPI(title="Notification Service", lifespan=lifespan)

# ВАЖНО: регистрируем роутеры
app.include_router(internal_events_router)
app.include_router(notification_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}