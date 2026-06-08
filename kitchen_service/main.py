from contextlib import asynccontextmanager
import os
import asyncio

from fastapi import FastAPI

from api.internal_events_router import router as internal_events_router
from api.kitchen_router import router as kitchen_router
from db.db import init_models
from services.event_consumer import KitchenEventConsumer
from common.correlation import correlation_id_middleware

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

consumer = KitchenEventConsumer(rabbit_url=RABBITMQ_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    task = asyncio.create_task(consumer.start())
    try:
        yield
    finally:
        await consumer.close()
        task.cancel()


app = FastAPI(title="Kitchen Service", lifespan=lifespan)
app.middleware("http")(correlation_id_middleware)

app.include_router(internal_events_router)
app.include_router(kitchen_router)


@app.get("/health")
def health():
    return {"status": "ok"}